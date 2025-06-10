import time
import re
from decimal import Decimal
from models.database import get_db_connection
from models.assessment import Assessment  # Import your assessment model

class PartialCreditAutoGrader:
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.connections = []
        self.max_connections = 3
        self.late_penalty_rate = 0.10  # 10% penalty for late submissions
    
    def get_connection(self):
        if self.connections:
            return self.connections.pop()
        return get_db_connection()
    
    def return_connection(self, conn):
        try:
            conn.rollback()
            if len(self.connections) < self.max_connections:
                self.connections.append(conn)
            else:
                conn.close()
        except:
            pass

    def get_fresh_connection(self):
        """Get a completely fresh connection for isolated testing"""
        return get_db_connection()

    def cleanup_test_environment(self, cursor, test_steps):
        """Comprehensive cleanup of test environment"""
        try:
            # Run explicit cleanup/after steps
            cleanup_steps = [s for s in test_steps if s['type'] == 'after']
            for step in cleanup_steps:
                try:
                    print(f"DEBUG: Running cleanup: {step['sql']}")
                    cursor.execute(step['sql'])
                except Exception as e:
                    print(f"DEBUG: Cleanup step error: {str(e)}")
                    pass
            
            # Extract table names from setup steps and drop them
            setup_steps = [s for s in test_steps if s['type'] in ('setup', 'before')]
            tables_to_drop = set()
            
            for step in setup_steps:
                # Find CREATE TABLE statements
                create_matches = re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', 
                                          step['sql'], re.IGNORECASE)
                tables_to_drop.update(create_matches)
            
            # Drop all identified tables
            for table_name in tables_to_drop:
                try:
                    print(f"DEBUG: Dropping table: {table_name}")
                    cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                except Exception as e:
                    print(f"DEBUG: Error dropping table {table_name}: {str(e)}")
                    pass
            
            return True
        except Exception as e:
            print(f"DEBUG: Cleanup environment error: {str(e)}")
            return False

    def normalize_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, Decimal)):
            return float(value) if isinstance(value, Decimal) else value
        if hasattr(value, 'date'):
            return value.date() if hasattr(value, 'date') else value
        return str(value)

    def normalize_row(self, row):
        """Normalize a database row for comparison"""
        if isinstance(row, dict):
            return tuple(self.normalize_value(v) for v in row.values())
        elif isinstance(row, (tuple, list)):
            return tuple(self.normalize_value(v) for v in row)
        else:
            return (self.normalize_value(row),)

    def calculate_partial_score(self, student_result, expected_result):
        """Calculate partial score based on how many tuples match"""
        print(f"DEBUG: Raw student result: {student_result}")
        print(f"DEBUG: Raw expected result: {expected_result}")
        
        if not expected_result:
            return {'score': 1.0, 'matched_count': 0} if not student_result else {'score': 0.0, 'matched_count': 0}
        
        if not student_result:
            return {'score': 0.0, 'matched_count': 0}
        
        # Normalize both results
        student_normalized = [self.normalize_row(row) for row in student_result]
        expected_normalized = [self.normalize_row(row) for row in expected_result]
        
        print(f"DEBUG: Normalized student: {student_normalized}")
        print(f"DEBUG: Normalized expected: {expected_normalized}")
        
        # Count exact matches
        matched_count = 0
        student_copy = student_normalized.copy()
        
        for i, expected_tuple in enumerate(expected_normalized):
            print(f"DEBUG: Looking for expected tuple {i}: {expected_tuple}")
            
            # Check if this tuple exists in student results
            found = False
            for j, student_tuple in enumerate(student_copy):
                print(f"DEBUG: Comparing with student tuple {j}: {student_tuple}")
                
                if student_tuple == expected_tuple:
                    matched_count += 1
                    student_copy.remove(student_tuple)  # Remove to handle duplicates correctly
                    found = True
                    print(f"DEBUG: Match found! Total matches: {matched_count}")
                    break
            
            if not found:
                print(f"DEBUG: No match found for expected tuple: {expected_tuple}")
        
        # Calculate score as ratio of matched tuples
        total_expected = len(expected_normalized)
        score = matched_count / total_expected if total_expected > 0 else 0.0
        
        print(f"DEBUG: Final matched_count: {matched_count}, total_expected: {total_expected}, score: {score}")
        
        return {
            'score': score,
            'matched_count': matched_count
        }

    def execute_with_timeout(self, cursor, sql_code, timeout=10):
        """Execute SQL with timeout, handling multiple statements"""
        try:
            print(f"DEBUG: Full SQL code to execute: {sql_code}")
            
            # Split multiple statements
            statements = [stmt.strip() for stmt in sql_code.split(';') if stmt.strip()]
            print(f"DEBUG: Split into {len(statements)} statements: {statements}")
            
            last_select_result = None
            execution_results = []
            
            for i, statement in enumerate(statements):
                print(f"DEBUG: Executing statement {i+1}: {statement}")
                cursor.execute(statement)
                
                # Only fetch results for SELECT statements
                if statement.upper().strip().startswith('SELECT'):
                    rows = cursor.fetchall()
                    last_select_result = rows
                    execution_results.append(f"SELECT returned {len(rows)} rows")
                    print(f"DEBUG: SELECT result: {rows}")
                else:
                    # For non-SELECT statements, check affected rows
                    affected_rows = cursor.rowcount
                    execution_results.append(f"{statement.split()[0].upper()} affected {affected_rows} rows")
                    print(f"DEBUG: Non-SELECT statement executed, affected rows: {affected_rows}")
            
            print(f"DEBUG: Execution summary: {execution_results}")
            
            # Return the last SELECT result, or empty list if no SELECT
            return last_select_result if last_select_result is not None else [], None
            
        except Exception as e:
            print(f"DEBUG: Exception in execute_with_timeout: {str(e)}")
            raise e

    def setup_clean_environment(self, cursor, steps):
        """Setup a completely clean test environment"""
        try:
            print("DEBUG: Setting up clean environment")
            
            # First, clean up any existing tables
            self.cleanup_test_environment(cursor, steps)
            
            # Run setup steps
            setup_steps = [s for s in steps if s['type'] in ('setup', 'before')]
            for step in setup_steps:
                print(f"DEBUG: Running setup: {step['sql']}")
                cursor.execute(step['sql'])
            
            print("DEBUG: Clean environment setup completed")
            return True
            
        except Exception as e:
            print(f"DEBUG: Setup clean environment error: {str(e)}")
            return False

    def get_test_data(self, cursor, tid):
        cursor.execute("""
            SELECT tc.tcid, tc.title, tc.weight,
                   ts.step_type, ts.sql_code, ts.is_model_answer
            FROM test_cases tc
            LEFT JOIN test_steps ts ON tc.tcid = ts.tcid
            WHERE tc.tid = %s
            ORDER BY tc.tcid, ts.tsid
        """, (tid,))
        
        rows = cursor.fetchall()
        cases = {}
        
        for row in rows:
            tcid = row['tcid']
            if tcid not in cases:
                cases[tcid] = {'title': row['title'], 'weight': row['weight'], 'steps': []}
            if row['step_type']:
                cases[tcid]['steps'].append({
                    'type': row['step_type'],
                    'sql': row['sql_code'],
                    'is_model': row['is_model_answer']
                })
        
        return list(cases.values())

    def run_test_case(self, test_case, student_code):
        """Run a single test case with complete isolation"""
        title = test_case['title']
        weight = test_case['weight']
        steps = test_case['steps']
        
        print(f"DEBUG: Starting test case: {title}")
        
        # Use fresh connections for complete isolation
        model_conn = self.get_fresh_connection()
        student_conn = self.get_fresh_connection()
        
        try:
            # ===== EXECUTE MODEL ANSWER IN ISOLATED ENVIRONMENT =====
            model_cursor = model_conn.cursor(dictionary=True)
            
            try:
                # Setup clean environment for model
                if not self.setup_clean_environment(model_cursor, steps):
                    return {
                        'success': False,
                        'weight': weight,
                        'score': 0.0,
                        'student_output': "Setup Error: Failed to setup model environment",
                        'scoring_data': "N/A",
                        'similarity_info': "0/0 tuples matched"
                    }
                
                model_conn.commit()
                
                # Get and execute model answer
                model_steps = [s for s in steps if s['type'] == 'execution' and s['is_model']]
                if not model_steps:
                    return {
                        'success': False,
                        'weight': weight,
                        'score': 0.0,
                        'student_output': "Error: No model answer",
                        'scoring_data': "N/A",
                        'similarity_info': "0/0 tuples matched"
                    }
                
                print(f"DEBUG: Executing model answer: {model_steps[0]['sql']}")
                expected, _ = self.execute_with_timeout(model_cursor, model_steps[0]['sql'])
                print(f"DEBUG: Model result: {expected}")
                
            except Exception as e:
                print(f"DEBUG: Model execution error: {str(e)}")
                return {
                    'success': False,
                    'weight': weight,
                    'score': 0.0,
                    'student_output': "Error: Model execution failed",
                    'scoring_data': f"Model Error: {str(e)}",
                    'similarity_info': "0/0 tuples matched"
                }
            finally:
                try:
                    self.cleanup_test_environment(model_cursor, steps)
                    model_conn.commit()
                    model_cursor.close()
                    model_conn.close()
                except:
                    pass
            
            # ===== EXECUTE STUDENT CODE IN FRESH ISOLATED ENVIRONMENT =====
            student_cursor = student_conn.cursor(dictionary=True)
            
            try:
                # Setup fresh clean environment for student
                if not self.setup_clean_environment(student_cursor, steps):
                    return {
                        'success': False,
                        'weight': weight,
                        'score': 0.0,
                        'student_output': "Setup Error: Failed to setup student environment",
                        'scoring_data': self.format_result_for_display(expected),
                        'similarity_info': f"0/{len(expected) if expected else 0} tuples matched"
                    }
                
                student_conn.commit()
                
                # Execute student code
                print(f"DEBUG: Executing student code: {student_code}")
                student_result, _ = self.execute_with_timeout(student_cursor, student_code)
                print(f"DEBUG: Student result: {student_result}")
                
            except Exception as e:
                print(f"DEBUG: Student execution error: {str(e)}")
                return {
                    'success': False,
                    'weight': weight,
                    'score': 0.0,
                    'student_output': f"Query Error: {str(e)}",
                    'scoring_data': self.format_result_for_display(expected),
                    'similarity_info': f"0/{len(expected) if expected else 0} tuples matched"
                }
            finally:
                try:
                    self.cleanup_test_environment(student_cursor, steps)
                    student_conn.commit()
                    student_cursor.close()
                    student_conn.close()
                except:
                    pass
            
            # ===== CALCULATE SCORE =====
            score_info = self.calculate_partial_score(student_result, expected)
            partial_score = score_info['score']
            matched_tuples = score_info.get('matched_count', 0)
            total_tuples = len(expected) if expected else 0
            
            print(f"DEBUG: Test case completed - Score: {partial_score:.2%}")
            
            return {
                'success': partial_score >= 0.8,
                'weight': weight,
                'score': partial_score,
                'student_output': self.format_result_for_display(student_result),
                'scoring_data': self.format_result_for_display(expected),
                'similarity_info': f"{matched_tuples}/{total_tuples} tuples matched"
            }
            
        except Exception as e:
            print(f"DEBUG: Test case error: {str(e)}")
            return {
                'success': False,
                'weight': weight,
                'score': 0.0,
                'student_output': f"Test Error: {str(e)}",
                'scoring_data': "N/A",
                'similarity_info': "0/0 tuples matched"
            }

    def format_result_for_display(self, result):
        """Format result for display in feedback"""
        if not result:
            return "Empty result"
        
        try:
            # Convert to readable format
            formatted_rows = []
            for row in result[:10]:  # Show max 10 rows
                if isinstance(row, dict):
                    # Convert dict to tuple of values
                    formatted_rows.append(str(tuple(row.values())))
                elif isinstance(row, (tuple, list)):
                    formatted_rows.append(str(tuple(row)))
                else:
                    formatted_rows.append(str(row))
            
            output = "\n".join(formatted_rows)
            if len(result) > 10:
                output += f"\n... ({len(result)} total rows)"
            
            return output
        except Exception as e:
            return f"Display error: {str(e)}"

    def check_late_submission(self, aid):
        """Check if submission is late and calculate penalty"""
        try:
            # Check if submission is late using assessment due date
            is_late = Assessment.is_submission_late(aid)
            
            if is_late:
                return {
                    'is_late': True,
                    'penalty_rate': self.late_penalty_rate,
                    'penalty_message': f"⚠️ Late Submission Penalty: {self.late_penalty_rate * 100}% score reduction applied"
                }
            else:
                return {
                    'is_late': False,
                    'penalty_rate': 0,
                    'penalty_message': "✅ Submitted on time - no penalty applied"
                }
        except Exception as e:
            print(f"DEBUG: Error checking late submission: {str(e)}")
            # If we can't check, assume not late
            return {
                'is_late': False,
                'penalty_rate': 0,
                'penalty_message': "✅ No penalty applied"
            }

    def get_submissions_to_regrade(self, aid):
        """Get all submissions that need re-grading after due date change"""
        conn = self.get_fresh_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT s.username, s.tid, s.submit_at, g.score as original_score
                FROM submissions s
                JOIN grades g ON s.username = g.username 
                    AND s.aid = g.aid 
                    AND s.tid = g.tid
                WHERE s.aid = %s
                ORDER BY s.submit_at DESC
            """, (aid,))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching submissions to re-grade: {str(e)}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def re_grade_after_due_date_change(self, aid):
        """Re-grade all submissions after due date change"""
        submissions = self.get_submissions_to_regrade(aid)
        results = {
            'total': len(submissions),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        for sub in submissions:
            try:
                # Get the original submission code
                conn = self.get_fresh_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT code FROM submissions
                    WHERE username = %s AND aid = %s AND tid = %s
                """, (sub['username'], aid, sub['tid']))
                
                code_result = cursor.fetchone()
                if not code_result or not code_result['code']:
                    results['details'].append({
                        'username': sub['username'],
                        'tid': sub['tid'],
                        'status': 'failed',
                        'reason': 'No code found'
                    })
                    results['failed'] += 1
                    continue
                
                # Re-grade with original code
                success = self.auto_grade(
                    username=sub['username'],
                    aid=aid,
                    tid=sub['tid'],
                    code=code_result['code'],
                    is_re_grade=True
                )
                
                if success:
                    results['success'] += 1
                    results['details'].append({
                        'username': sub['username'],
                        'tid': sub['tid'],
                        'status': 'success',
                        'original_score': sub['original_score']
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'username': sub['username'],
                        'tid': sub['tid'],
                        'status': 'failed',
                        'reason': 'Grading error'
                    })
                    
            except Exception as e:
                print(f"Re-grade error for {sub['username']}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'username': sub['username'],
                    'tid': sub['tid'],
                    'status': 'failed',
                    'reason': str(e)
                })
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
        
        return results

    def auto_grade(self, username, aid, tid, code, is_re_grade=False):
        """Main auto-grading function with re-grade support"""
        start_time = time.time()
        
        print(f"DEBUG: {'Re-' if is_re_grade else ''}Grading for {username}, aid={aid}, tid={tid}")
        print(f"DEBUG: Code: {code}")
        
        # Check for late submission
        late_info = self.check_late_submission(aid)
        print(f"DEBUG: Late submission check: {late_info}")
        
        # Use a separate connection just for metadata
        meta_conn = self.get_fresh_connection()
        meta_cursor = meta_conn.cursor(dictionary=True)
        
        try:
            # Get task info
            meta_cursor.execute("""
                SELECT t.max_score, COUNT(tc.tcid) as count, SUM(tc.weight) as total_weight
                FROM tasks t
                LEFT JOIN test_cases tc ON t.tid = tc.tid
                WHERE t.tid = %s AND t.aid = %s
            """, (tid, aid))
            
            task = meta_cursor.fetchone()
            if not task or task['count'] == 0:
                print(f"DEBUG: No task found for tid={tid}, aid={aid}")
                return False
            
            max_score = task['max_score'] or 100
            total_weight = task['total_weight'] or 1
            
            print(f"DEBUG: Task found - max_score: {max_score}, total_weight: {total_weight}")
            
            # Get test cases
            test_cases = self.get_test_data(meta_cursor, tid)
            print(f"DEBUG: Found {len(test_cases)} test cases")
            
            # Run tests with complete isolation
            total_score = 0
            feedback_html = []
            passed = 0
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"DEBUG: Running test case {i}: {test_case['title']}")
                test_case_start = time.time()
                
                # Each test case runs in complete isolation
                result = self.run_test_case(test_case, code)
                
                test_case_time = time.time() - test_case_start
                
                # Format as HTML for feedback
                test_feedback = f"""
                <div style="margin-bottom: 20px; border-bottom: 1px solid #ddd; padding-bottom: 15px;">
                    <h6>Test Case {i}: {test_case['title']}</h6>
                    <ul>
                        <li><strong>Query Output:</strong><br>
                            <pre style="background: #f8f9fa; padding: 10px; margin: 5px 0; white-space: pre-wrap;">{result['student_output']}</pre>
                        </li>
                        <li><strong>Expected Output:</strong><br>
                            <pre style="background: #f8f9fa; padding: 10px; margin: 5px 0; white-space: pre-wrap;">{result['scoring_data']}</pre>
                        </li>
                        <li><strong>Execution Time:</strong> {test_case_time:.3f}s</li>
                        <li><strong>Answer Similarity:</strong> {result['similarity_info']}</li>
                        <li><strong>Score:</strong> {result['score']:.2%}</li>
                    </ul>
                </div>
                """
                feedback_html.append(test_feedback)
                
                # Calculate weighted score
                partial_score = float(result.get('score', 0.0))
                weight = float(result['weight'])
                total_weight_float = float(total_weight)
                max_score_float = float(max_score)
                
                total_score += (partial_score * weight / total_weight_float) * max_score_float
                
                if result['success']:
                    passed += 1
                
                print(f"DEBUG: Test case {i} completed - score: {partial_score}, success: {result['success']}")
            
            # Calculate original score before penalty
            original_score = round(total_score, 2)
            
            # Apply late penalty if applicable
            if late_info['is_late']:
                penalty_amount = original_score * late_info['penalty_rate']
                final_score = round(max(0, original_score - penalty_amount), 2)
                print(f"DEBUG: Late penalty applied - Original: {original_score}, Penalty: {penalty_amount}, Final: {final_score}")
            else:
                final_score = original_score
                print(f"DEBUG: No penalty - Final score: {final_score}")
            
            # Add late penalty information to feedback
            penalty_feedback = f"""
            <div style="margin-bottom: 20px; padding: 15px; border: 2px solid {'#ffc107' if late_info['is_late'] else '#28a745'}; border-radius: 5px; background-color: {'#fff3cd' if late_info['is_late'] else '#d4edda'};">
                <h6 style="color: {'#856404' if late_info['is_late'] else '#155724'};">Submission Status</h6>
                <p style="margin: 5px 0; color: {'#856404' if late_info['is_late'] else '#155724'};">{late_info['penalty_message']}</p>
                {f'<p style="margin: 5px 0; color: #856404;"><strong>Original Score:</strong> {original_score} | <strong>Final Score:</strong> {final_score}</p>' if late_info['is_late'] else ''}
            </div>
            """
            
            # Combine all feedback
            feedback_text = penalty_feedback + "".join(feedback_html)
            
            print(f"DEBUG: Final score after penalty: {final_score}")
            
            # Save grade (this overwrites any previous grade)
            meta_cursor.execute("""
                INSERT INTO grades (username, aid, tid, score, feedback, graded_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                score = VALUES(score), feedback = VALUES(feedback), graded_at = VALUES(graded_at)
            """, (username, aid, tid, final_score, feedback_text))
            
            meta_conn.commit()
            print(f"DEBUG: Grade saved successfully")
            return True
            
        except Exception as e:
            print(f"Auto-grading error: {str(e)}")
            meta_conn.rollback()
            return False
        finally:
            try:
                meta_cursor.close()
                meta_conn.close()
            except:
                pass

# Global instance
_grader = None

def get_grader():
    global _grader
    if _grader is None:
        _grader = PartialCreditAutoGrader()
    return _grader

def auto_grade(username, aid, tid, code):
    """Main auto-grading function"""
    return get_grader().auto_grade(username, aid, tid, code)
