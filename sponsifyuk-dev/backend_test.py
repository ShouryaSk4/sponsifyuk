#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time

class SponsifyUKAPITester:
    def __init__(self, base_url="https://sponsor-finder-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = None
        self.test_user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", expected_status=None, actual_status=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            if expected_status and actual_status:
                print(f"   Expected: {expected_status}, Got: {actual_status}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "expected_status": expected_status,
            "actual_status": actual_status
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.session_token:
            test_headers['Authorization'] = f'Bearer {self.session_token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.log_test(name, True, expected_status=expected_status, actual_status=response.status_code)
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', str(error_data))
                except:
                    error_detail = response.text[:200]
                
                self.log_test(name, False, error_detail, expected_status, response.status_code)
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Request failed: {str(e)}")
            return False, {}

    def test_basic_endpoints(self):
        """Test basic non-auth endpoints"""
        print("\n🔍 Testing Basic Endpoints...")
        
        # Test jobs endpoint (should work without auth)
        success, jobs_data = self.run_test(
            "Get Jobs List",
            "GET",
            "jobs",
            200
        )
        
        if success and isinstance(jobs_data, list):
            print(f"   Found {len(jobs_data)} jobs")
            if len(jobs_data) > 0:
                # Test individual job endpoint
                first_job_id = jobs_data[0].get('id')
                if first_job_id:
                    self.run_test(
                        "Get Individual Job",
                        "GET",
                        f"jobs/{first_job_id}",
                        200
                    )
        
        # Test jobs with filters
        self.run_test(
            "Get Jobs with Industry Filter",
            "GET",
            "jobs?industry=Technology",
            200
        )
        
        self.run_test(
            "Get Jobs with Search",
            "GET",
            "jobs?search=developer",
            200
        )

    def test_auth_endpoints_without_token(self):
        """Test auth endpoints without authentication (should fail)"""
        print("\n🔍 Testing Auth Endpoints (No Token)...")
        
        self.run_test(
            "Get User Profile (No Auth)",
            "GET",
            "auth/me",
            401
        )
        
        self.run_test(
            "Get User Saved Jobs (No Auth)",
            "GET",
            "user/saved-jobs",
            401
        )
        
        self.run_test(
            "Get Membership Status (No Auth)",
            "GET",
            "user/membership-status",
            401
        )

    def create_test_user_session(self):
        """Create a test user and session in MongoDB for testing"""
        print("\n🔍 Creating Test User Session...")
        
        try:
            import subprocess
            
            # Generate unique IDs
            timestamp = str(int(time.time()))
            user_id = f"test-user-{timestamp}"
            session_token = f"test_session_{timestamp}"
            
            # MongoDB command to create test user and session
            mongo_cmd = f"""
            use('test_database');
            db.users.insertOne({{
              id: '{user_id}',
              email: 'test.user.{timestamp}@example.com',
              name: 'Test User {timestamp}',
              picture: 'https://via.placeholder.com/150',
              membership_type: 'free',
              job_views_count: 0,
              bio: null,
              phone: null,
              location: null,
              created_at: new Date().toISOString()
            }});
            db.user_sessions.insertOne({{
              user_id: '{user_id}',
              session_token: '{session_token}',
              expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
              created_at: new Date().toISOString()
            }});
            print('SUCCESS: Created user and session');
            """
            
            result = subprocess.run(
                ['mongosh', '--eval', mongo_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and 'SUCCESS' in result.stdout:
                self.session_token = session_token
                self.test_user_id = user_id
                print(f"✅ Created test user: {user_id}")
                print(f"✅ Created session token: {session_token}")
                return True
            else:
                print(f"❌ Failed to create test user: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating test user: {str(e)}")
            return False

    def test_auth_endpoints_with_token(self):
        """Test auth endpoints with valid token"""
        if not self.session_token:
            print("❌ No session token available for auth testing")
            return
            
        print("\n🔍 Testing Auth Endpoints (With Token)...")
        
        # Test get current user
        success, user_data = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        
        if success:
            print(f"   User: {user_data.get('name', 'Unknown')} ({user_data.get('email', 'No email')})")
        
        # Test membership status
        success, membership_data = self.run_test(
            "Get Membership Status",
            "GET",
            "user/membership-status",
            200
        )
        
        if success:
            print(f"   Membership: {membership_data.get('membership_type', 'Unknown')}")
            print(f"   Job Views: {membership_data.get('job_views_count', 0)}/{membership_data.get('job_views_limit', 'Unlimited')}")

    def test_job_operations(self):
        """Test job-related operations"""
        if not self.session_token:
            print("❌ No session token available for job operations testing")
            return
            
        print("\n🔍 Testing Job Operations...")
        
        # Get jobs to find one to save
        success, jobs_data = self.run_test(
            "Get Jobs for Save Test",
            "GET",
            "jobs",
            200
        )
        
        if success and isinstance(jobs_data, list) and len(jobs_data) > 0:
            test_job_id = jobs_data[0].get('id')
            
            if test_job_id:
                # Test save job
                success, save_result = self.run_test(
                    "Save Job",
                    "POST",
                    f"user/save-job/{test_job_id}",
                    200
                )
                
                if success:
                    # Test get saved jobs
                    success, saved_jobs = self.run_test(
                        "Get Saved Jobs",
                        "GET",
                        "user/saved-jobs",
                        200
                    )
                    
                    if success:
                        print(f"   Found {len(saved_jobs)} saved jobs")
                    
                    # Test unsave job
                    self.run_test(
                        "Unsave Job",
                        "DELETE",
                        f"user/save-job/{test_job_id}",
                        200
                    )

    def test_profile_operations(self):
        """Test profile operations"""
        if not self.session_token:
            print("❌ No session token available for profile testing")
            return
            
        print("\n🔍 Testing Profile Operations...")
        
        # Test get profile
        success, profile_data = self.run_test(
            "Get User Profile",
            "GET",
            "user/profile",
            200
        )
        
        if success:
            # Test update profile
            update_data = {
                "name": "Updated Test User",
                "bio": "This is a test bio",
                "phone": "+44 123 456 7890",
                "location": "London, UK"
            }
            
            success, updated_profile = self.run_test(
                "Update User Profile",
                "PUT",
                "user/profile",
                200,
                data=update_data
            )
            
            if success:
                print(f"   Updated profile: {updated_profile.get('name', 'Unknown')}")

    def test_membership_limits(self):
        """Test free membership limits"""
        if not self.session_token:
            print("❌ No session token available for membership limit testing")
            return
            
        print("\n🔍 Testing Membership Limits...")
        
        # Make multiple job requests to test the 10-view limit
        for i in range(12):  # Try to exceed the limit
            success, _ = self.run_test(
                f"Job View {i+1} (Testing Limits)",
                "GET",
                "jobs",
                200 if i < 10 else 403  # Should fail after 10 views
            )
            
            if not success and i >= 10:
                print(f"   ✅ Membership limit enforced at view {i+1}")
                break

    def cleanup_test_data(self):
        """Clean up test data"""
        if not self.test_user_id:
            return
            
        print("\n🧹 Cleaning up test data...")
        
        try:
            import subprocess
            
            mongo_cmd = f"""
            use('test_database');
            db.users.deleteOne({{id: '{self.test_user_id}'}});
            db.user_sessions.deleteOne({{user_id: '{self.test_user_id}'}});
            db.saved_jobs.deleteMany({{user_id: '{self.test_user_id}'}});
            print('CLEANUP: Removed test data');
            """
            
            result = subprocess.run(
                ['mongosh', '--eval', mongo_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Test data cleaned up")
            else:
                print(f"⚠️  Cleanup warning: {result.stderr}")
                
        except Exception as e:
            print(f"⚠️  Cleanup error: {str(e)}")

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting SponsifyUK API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Test basic endpoints first
        self.test_basic_endpoints()
        
        # Test auth endpoints without token
        self.test_auth_endpoints_without_token()
        
        # Create test user and session
        if self.create_test_user_session():
            # Test auth endpoints with token
            self.test_auth_endpoints_with_token()
            
            # Test job operations
            self.test_job_operations()
            
            # Test profile operations
            self.test_profile_operations()
            
            # Test membership limits
            self.test_membership_limits()
            
            # Clean up
            self.cleanup_test_data()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = SponsifyUKAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': (tester.tests_passed/tester.tests_run*100) if tester.tests_run > 0 else 0,
            'results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())