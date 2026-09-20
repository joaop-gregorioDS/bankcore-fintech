using BankCore.Risk.Application;
using Xunit;

namespace BankCore.Risk.UnitTests;

public sealed class RiskRuntimeOptionsTests
{
    [Fact]
    public void Defaults_describe_a_safe_production_like_runtime()
    {
        var options = new RiskRuntimeOptions();

        Assert.Equal("bankcore-risk", options.ServiceName);
        Assert.Equal("Production", options.EnvironmentName);
    }
}
