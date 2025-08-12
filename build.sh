tag=1

echo "=== metrics ==="

image_name="abdumajidnumeo/mock-agent-service"

docker build . --file Dockerfile --platform linux/amd64 --tag $image_name:$tag

docker push $image_name:$tag
