namespace BankCore.Risk.Domain.Rules;

public interface IRiskRule
{
    string Name { get; }

    RiskRuleResult Evaluate(RiskRuleContext context);
}
