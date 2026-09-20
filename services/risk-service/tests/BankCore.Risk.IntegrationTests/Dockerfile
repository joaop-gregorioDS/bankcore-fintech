FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine@sha256:3111b113abec80b4a8a3d4b5cebebf61a4cdab019b7e56ca3e6389e6ac4e1c8d
WORKDIR /src
COPY services/risk-service ./services/risk-service
RUN dotnet restore services/risk-service/tests/BankCore.Risk.IntegrationTests/BankCore.Risk.IntegrationTests.csproj
RUN dotnet build services/risk-service/tests/BankCore.Risk.IntegrationTests/BankCore.Risk.IntegrationTests.csproj --configuration Release --no-restore
ENTRYPOINT ["dotnet", "test", "services/risk-service/tests/BankCore.Risk.IntegrationTests/BankCore.Risk.IntegrationTests.csproj", "--configuration", "Release", "--no-build", "--logger", "console;verbosity=minimal"]
