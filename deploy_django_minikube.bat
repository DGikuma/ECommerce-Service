@echo off
echo =====================================================
echo 🚀 Django Minikube Deployment Script
echo =====================================================

:: Step 1: Configure Docker to use Minikube's daemon
echo [1/5] Configuring Docker to use Minikube...
FOR /F "tokens=*" %%i IN ('minikube docker-env') DO %%i

:: Step 2: Build the Django image inside Minikube
echo [2/5] Building Django Docker image inside Minikube...
docker build -t your-django-image:latest .

:: Step 3: Apply Kubernetes deployment + service
echo [3/5] Applying Kubernetes manifests...
kubectl apply -f deployment.yaml
kubectl apply -f postgres-deployment.yaml

:: Step 4: Restart Django pod to use fresh image
echo [4/5] Restarting Django pod...
kubectl delete pod -l app=django

:: Step 5: Wait for pod to be ready and open service URL
echo [5/5] Waiting for Django pod to be ready...
kubectl rollout status deployment/django-app

echo Opening Django service URL in browser...
minikube service django-service --url

echo =====================================================
echo ✅ Deployment complete!
echo =====================================================
pause
