FROM eclipse-temurin:17-jdk-alpine AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir -r src/main/python/requirements.txt || true
RUN sed -i 's|src/main/python/anomaly_detector.py|/app/python/anomaly_detector.py|g' src/main/resources/application.yml || true

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
RUN apk add --no-cache python3 py3-pip
COPY --from=build /usr/lib/python3*/site-packages /usr/lib/python3*/site-packages || true
COPY src/main/python/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || true
COPY target/*.jar app.jar
COPY src/main/python /app/python
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
