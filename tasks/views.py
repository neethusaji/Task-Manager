from django.contrib.auth.models import User
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import datetime, timedelta
from tasks.models import OTP, Task
from tasks.utils import send_otp_email
from .serializers import OTPLoginSerializer, TaskSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.views import APIView

# Login View
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  
def login_view(request):
    # Extract username and password from the request data
    email = request.data.get('email')
    password = request.data.get('password')

    # Validate input
    if not email or not password:
        return Response({'detail': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the user exists and validate password
    user = User.objects.filter(email=email).first()
    if user and user.check_password(password):
        refresh = RefreshToken.for_user(user)
        return Response({
            'username': user.username,
            'token': str(refresh.access_token),
        })
    return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

# Register View
@api_view(['POST'])
@permission_classes([permissions.AllowAny]) 
def register_view(request):
    # Extract the user data from the request
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email') 

    # Basic validation for required fields
    if not username or not password:
        return Response({'detail': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate that the password meets the criteria (you can customize this)
    try:
        validate_password(password)
    except ValidationError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the username already exists
    if User.objects.filter(username=username).exists():
        return Response({'detail': 'Username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create the user
    user = User.objects.create_user(username=username, password=password, email=email)
    
    # Optionally, you can return some user data (avoid sending password back)
    return Response({
        'username': user.username,
        'email': user.email,
    }, status=status.HTTP_201_CREATED)

# Create Task
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated]) 
def create_task(request):
    if request.method == 'POST':
        # Deserialize the incoming data
        serializer = TaskSerializer(data=request.data)
        
        if serializer.is_valid():
            # Save the new task to the database
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])  
@permission_classes([permissions.IsAuthenticated])  # Require authentication
def delete_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return Response({'detail': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)

    task.delete()  # Delete the task
    return Response({'detail': 'Task deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


# Update Task
@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated]) 
def update_task(request, task_id):
    try:
        task = Task.objects.get(id=task_id)  # Fetch the task by its ID
    except Task.DoesNotExist:
        return Response({'detail': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    # Validate and update the task
    serializer = TaskSerializer(task, data=request.data, partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_tasks_calendar(request):
    """Fetch all tasks and group them by their due date"""
    try:
        # Get the current date (today) and the beginning of the week
        today = timezone.now().date()

        # Fetch all tasks
        tasks = Task.objects.all().order_by('due_date')

        tasks_by_date = {}
        
        # Group tasks by their due date
        for task in tasks:
            due_date_str = task.due_date.date().strftime('%Y-%m-%d')  # Format date as string
            if due_date_str not in tasks_by_date:
                tasks_by_date[due_date_str] = []
            tasks_by_date[due_date_str].append({
                'title': task.title,
                'description': task.description,
                'due_date': task.due_date.date().strftime('%Y-%m-%d'),
            })
        
        return Response(tasks_by_date, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Get All Tasks (New API)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_all_tasks(request):
    # Fetch all tasks for the authenticated user
    tasks = Task.objects.all().order_by('due_date')  # You can order tasks by any field as needed
    
    # Serialize the tasks using the TaskSerializer
    serializer = TaskSerializer(tasks, many=True)
    
    # Return the serialized data in the response
    return Response(serializer.data, status=status.HTTP_200_OK)

class OTPLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                otp_record = OTP.objects.get(user=user, otp=otp)
                if otp_record.is_expired():
                    return Response({"detail": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

                # If OTP is valid and not expired, authenticate user
                token = RefreshToken.for_user(user)
                return Response({
                    'username': user.username,
                    "token": str(token.access_token),
                }, status=status.HTTP_200_OK)

            except OTP.DoesNotExist:
                return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        
        otp_record = send_otp_email(user)
        
        return Response({"detail": "OTP sent successfully to your email."}, status=status.HTTP_200_OK)
