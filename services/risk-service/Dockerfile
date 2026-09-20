FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine@sha256:3111b113abec80b4a8a3d4b5cebebf61a4cdab019b7e56ca3e6389e6ac4e1c8d AS build
WORKDIR /src

COPY services/risk-service ./services/risk-service
RUN dotnet restore services/risk-service/BankCore.Risk.sln
RUN dotnet publish services/risk-service/src/BankCore.Risk.Api/BankCore.Risk.Api.csproj \
    --configuration Release \
    --no-restore \
    --output /app/publish \
    /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine@sha256:628ffa789119d231880f32653b75aca3f528968058fdc3cdfb6969e583f8243a AS runtime
RUN addgroup -S -g 10001 bankcore \
    && adduser -S -D -u 10001 -G bankcore -h /nonexistent -s /sbin/nologin bankcore \
    && apk add --no-cache curl

WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:8080 \
    DOTNET_EnableDiagnostics=0

USER 10001
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
    CMD curl -fsS http://127.0.0.1:8080/readiness > /dev/null || exit 1

ENTRYPOINT ["dotnet", "BankCore.Risk.Api.dll"]
