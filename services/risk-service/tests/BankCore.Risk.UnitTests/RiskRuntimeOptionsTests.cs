using BankCore.Risk.Application;
using BankCore.Risk.Application.AssessRisk;
using BankCore.Risk.Domain.Assessments;
using BankCore.Risk.Domain.Rules;
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

    [Fact]
    public void Standard_amount_is_approved_with_zero_score()
    {
        var result = Assess(AmountRiskRule.StandardLimitCents);

        Assert.Equal(RiskDecision.Approved, result.Decision);
        Assert.Equal(0, result.RiskScore);
        Assert.Empty(result.Reasons);
    }

    [Fact]
    public void One_cent_above_standard_limit_requires_review()
    {
        var result = Assess(AmountRiskRule.StandardLimitCents + 1);

        Assert.Equal(RiskDecision.Review, result.Decision);
        Assert.Equal(40, result.RiskScore);
        Assert.Equal("HIGH_AMOUNT", Assert.Single(result.Reasons).Code);
    }

    [Fact]
    public void Critical_limit_is_still_the_high_amount_boundary()
    {
        var result = Assess(AmountRiskRule.CriticalLimitCents);

        Assert.Equal(RiskDecision.Review, result.Decision);
        Assert.Equal(40, result.RiskScore);
        Assert.Equal("HIGH_AMOUNT", Assert.Single(result.Reasons).Code);
    }

    [Fact]
    public void One_cent_above_critical_limit_is_rejected()
    {
        var result = Assess(AmountRiskRule.CriticalLimitCents + 1);

        Assert.Equal(RiskDecision.Rejected, result.Decision);
        Assert.Equal(70, result.RiskScore);
        Assert.Equal("VERY_HIGH_AMOUNT", Assert.Single(result.Reasons).Code);
    }

    [Fact]
    public void Same_input_produces_the_same_assessment()
    {
        var transactionId = Guid.Parse("11111111-1111-1111-1111-111111111111");
        var handler = new AssessRiskHandler();
        var command = new AssessRiskCommand(transactionId, 250_000, " pix ");

        var first = handler.Handle(command).Assessment;
        var second = handler.Handle(command).Assessment;

        Assert.Equal("PIX", command.OperationType);
        Assert.Equal(first.TransactionId, second.TransactionId);
        Assert.Equal(first.Decision, second.Decision);
        Assert.Equal(first.RiskScore, second.RiskScore);
        Assert.Equal(first.RulesVersion, second.RulesVersion);
        Assert.Equal(first.Reasons.Select(reason => reason.Code), second.Reasons.Select(reason => reason.Code));
        Assert.Equal(first.Reasons.Select(reason => reason.Points), second.Reasons.Select(reason => reason.Points));
    }

    [Fact]
    public void Rule_order_does_not_change_the_result_or_reason_order()
    {
        var command = new AssessRiskCommand(
            Guid.NewGuid(),
            AmountRiskRule.CriticalLimitCents + 1,
            "CARD");
        var normal = new AssessRiskHandler(new IRiskRule[] { new AmountRiskRule(), new OperationTypeRule() });
        var reversed = new AssessRiskHandler(new IRiskRule[] { new OperationTypeRule(), new AmountRiskRule() });

        var first = normal.Handle(command);
        var second = reversed.Handle(command);

        Assert.Equal(first.Decision, second.Decision);
        Assert.Equal(first.RiskScore, second.RiskScore);
        Assert.Equal(first.RulesVersion, second.RulesVersion);
        Assert.Equal(new[] { "UNSUPPORTED_OPERATION", "VERY_HIGH_AMOUNT" }, first.Reasons.Select(reason => reason.Code));
        Assert.Equal(first.Reasons.Select(reason => reason.Code), second.Reasons.Select(reason => reason.Code));
        Assert.Equal(first.Reasons.Select(reason => reason.Points), second.Reasons.Select(reason => reason.Points));
    }

    [Fact]
    public void Score_is_capped_at_100_when_rules_compose()
    {
        var result = Assess(AmountRiskRule.CriticalLimitCents + 1, "CARD");

        Assert.Equal(RiskDecision.Rejected, result.Decision);
        Assert.Equal(100, result.RiskScore);
    }

    [Fact]
    public void Rules_version_is_always_present_and_explicit()
    {
        var result = Assess(1);

        Assert.Equal(RiskRuleSet.CurrentVersion, result.RulesVersion);
        Assert.Equal("risk-rules-v1", result.RulesVersion);
    }

    [Fact]
    public void Decision_boundaries_are_explicit()
    {
        Assert.Equal(RiskDecision.Approved, RiskDecisionRules.FromScore(39));
        Assert.Equal(RiskDecision.Review, RiskDecisionRules.FromScore(40));
        Assert.Equal(RiskDecision.Review, RiskDecisionRules.FromScore(69));
        Assert.Equal(RiskDecision.Rejected, RiskDecisionRules.FromScore(70));
        Assert.Equal(RiskDecision.Rejected, RiskDecisionRules.FromScore(100));
    }

    [Fact]
    public void Operation_type_is_normalized_and_pix_is_supported()
    {
        var result = Assess(1, " pix ");

        Assert.Equal(RiskDecision.Approved, result.Decision);
        Assert.Equal(0, result.RiskScore);
    }

    [Fact]
    public void Unsupported_operation_adds_a_typed_reason()
    {
        var result = Assess(1, "CARD");

        Assert.Equal(RiskDecision.Review, result.Decision);
        Assert.Equal(40, result.RiskScore);
        var reason = Assert.Single(result.Reasons);
        Assert.Equal("UNSUPPORTED_OPERATION", reason.Code);
        Assert.Equal(40, reason.Points);
    }

    [Fact]
    public void Long_max_value_does_not_overflow_the_score()
    {
        var result = Assess(long.MaxValue);

        Assert.Equal(RiskDecision.Rejected, result.Decision);
        Assert.InRange(result.RiskScore, 0, 100);
    }

    [Fact]
    public void Invalid_commands_are_rejected_at_the_domain_boundary()
    {
        Assert.Throws<ArgumentException>(() => new AssessRiskCommand(Guid.Empty, 1, "PIX"));
        Assert.Throws<ArgumentOutOfRangeException>(() => new AssessRiskCommand(Guid.NewGuid(), 0, "PIX"));
        Assert.Throws<ArgumentException>(() => new AssessRiskCommand(Guid.NewGuid(), 1, " "));
        Assert.Throws<ArgumentException>(() => new AssessRiskCommand(Guid.NewGuid(), 1, "PIX", " "));
    }

    [Fact]
    public void Unsupported_rules_version_is_rejected()
    {
        var handler = new AssessRiskHandler();
        var command = new AssessRiskCommand(Guid.NewGuid(), 1, "PIX", "risk-rules-v2");

        Assert.Throws<ArgumentException>(() => handler.Handle(command));
    }

    private static AssessRiskResult Assess(long amountCents, string operationType = "PIX")
    {
        var handler = new AssessRiskHandler();
        return handler.Handle(new AssessRiskCommand(Guid.NewGuid(), amountCents, operationType));
    }
}
