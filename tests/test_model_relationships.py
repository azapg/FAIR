from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment


class TestModelRelationships:
    """Test the core academic workflow relationships"""
    
    def test_user_course_assignment_relationships(self, test_db):
        """
        Test that User -> Course -> Assignment relationships work properly.
        """
        with test_db() as session:
            professor_id = uuid4()
            professor = User(
                id=professor_id,
                name="Prof. Jane Smith",
                email="prof.smith@university.edu", 
                role=UserRole.professor
            )
            session.add(professor)
            session.commit()
            session.refresh(professor)
            
            course_id = uuid4()
            course = Course(
                id=course_id,
                name="Advanced Python Programming",
                description="Learn advanced Python concepts and patterns",
                instructor_id=professor_id
            )
            session.add(course)
            session.commit()
            session.refresh(course)
            
            assignment_id = uuid4()
            assignment = Assignment(
                id=assignment_id,
                course_id=course_id,
                title="Implement a Web API",
                description="Create a FastAPI application with authentication",
                deadline=datetime.now() + timedelta(days=14),
                max_grade={"points": 100}
            )
            session.add(assignment)
            session.commit()
            session.refresh(assignment)
            
            assert course.instructor is not None, "Course should have instructor relationship"
            assert course.instructor.id == professor_id, "Course instructor should be the professor we created"
            assert course.instructor.name == "Prof. Jane Smith", "Instructor name should match"
            
            assert assignment.course is not None, "Assignment should have course relationship"
            assert assignment.course.id == course_id, "Assignment course should be the course we created"
            assert assignment.course.name == "Advanced Python Programming", "Course name should match"
            
            assert len(professor.courses) > 0, "Professor should have courses relationship"
            assert professor.courses[0].id == course_id, "Professor's course should be the one we created"
            
            assert len(course.assignments) > 0, "Course should have assignments relationship"
            assert course.assignments[0].id == assignment_id, "Course's assignment should be the one we created"
            assert course.assignments[0].title == "Implement a Web API", "Assignment title should match"
    
    def test_foreign_key_constraints(self, test_db):
        """
        Test that foreign key constraints prevent orphaned records.
        
        This will fail until you have proper database constraints.
        """
        with test_db() as session:
            # Course without a valid instructor
            course = Course(
                id=uuid4(),
                name="Orphaned Course",
                description="This should fail",
                instructor_id=uuid4()  # Non-existent user ID
            )
            session.add(course)
            
            try:
                session.commit()
                assert False, "Expected IntegrityError when creating course with invalid instructor_id"
            except IntegrityError:
                session.rollback()
                pass
            
            assignment = Assignment(
                id=uuid4(),
                course_id=uuid4(),  # Non-existent course ID
                title="Orphaned Assignment",
                deadline=datetime.now() + timedelta(days=7),
                max_grade={"points": 50}
            )
            session.add(assignment)
            
            try:
                session.commit()
                assert False, "Expected IntegrityError when creating assignment with invalid course_id"
            except IntegrityError:
                session.rollback()
                pass
    
    def test_user_role_validation(self, test_db):
        """
        Test that user roles are properly validated.
        
        This will fail until you implement proper enum validation.
        """
        with test_db() as session:
            for role in [UserRole.admin, UserRole.professor, UserRole.student]:
                user = User(
                    id=uuid4(),
                    name=f"Test {role.value.title()}",
                    email=f"{role.value}@test.com",
                    role=role
                )
                session.add(user)
            
            session.commit()
            
            users = session.query(User).all()
            assert len(users) == 3, "Should have created 3 users"
            
            roles_found = {user.role for user in users}
            expected_roles = {UserRole.admin, UserRole.professor, UserRole.student}
            assert roles_found == expected_roles, f"Expected roles {expected_roles}, found {roles_found}"
    
    def test_assignment_deadline_validation(self, test_db):
        """
        Test that assignments handle datetime fields properly.
        
        This tests both database field types and Python datetime handling.
        """
        with test_db() as session:
            professor = User(
                id=uuid4(),
                name="Test Professor",
                email="test@prof.com",
                role=UserRole.professor
            )
            session.add(professor)
            session.commit()
            
            course = Course(
                id=uuid4(),
                name="Test Course",
                instructor_id=professor.id
            )
            session.add(course)
            session.commit()
            
            # Test assignment with future deadline
            future_deadline = datetime.now() + timedelta(days=30)
            assignment = Assignment(
                id=uuid4(),
                course_id=course.id,
                title="Future Assignment",
                deadline=future_deadline,
                max_grade={"points": 100}
            )
            session.add(assignment)
            session.commit()
            session.refresh(assignment)
            
            assert assignment.deadline is not None, "Assignment should have a deadline"
            assert isinstance(assignment.deadline, datetime), "Deadline should be datetime object"
            
            future_assignments = session.query(Assignment).filter(
                Assignment.deadline > datetime.now()
            ).all()
            assert len(future_assignments) > 0, "Should find assignments with future deadlines"
            assert assignment.id in [a.id for a in future_assignments], "Our assignment should be in future assignments"