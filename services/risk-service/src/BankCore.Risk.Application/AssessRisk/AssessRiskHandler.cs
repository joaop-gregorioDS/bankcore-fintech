using BankCore.Risk.Domain.Assessments;
using BankCore.Risk.Domain.Rules;

namespace BankCore.Risk.Application.AssessRisk;

public sealed class AssessRiskHandler
{
    private readonly IReadOnlyList<IRiskRule> _rules;

    public AssessRiskHandler()
        : this(RiskRuleSet.CreateV1())
    {
    }

    public AssessRiskHandler(IEnumerable<IRiskRule> rules)
    {
        ArgumentNullException.ThrowIfNull(rules);
        _rules = rules.ToArray();

        if (_rules.Count == 0)
        {
            throw new ArgumentException("At least one risk rule is required.", nameof(rules));
        }
    }

    public AssessRiskResult Handle(AssessRiskCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);

        if (!string.Equals(command.RulesVersion, RiskRuleSet.CurrentVersion, StringComparison.Ordinal))
        {
            throw new ArgumentException(
                $"Unsupported rules version: {command.RulesVersion}.",
                nameof(command));
        }

        var context = new RiskRuleContext(command.AmountCents, command.OperationType);
        var ruleResults = _rules.Select(rule => rule.Evaluate(context)).ToArray();

        var scorePoints = 0;
        foreach (var result in ruleResults)
        {
            scorePoints = result.Points >= 100 - scorePoints
                ? 100
                : scorePoints + result.Points;
        }

        var score = RiskScore.FromPoints(scorePoints);
        var reasons = ruleResults
            .SelectMany(result => result.Reasons)
            .OrderBy(reason => reason.Code, StringComparer.Ordinal)
            .ToArray();

        var assessment = new RiskAssessment(
            command.TransactionId,
            RiskDecisionRules.FromScore(score.Value),
            score,
            reasons,
            command.RulesVersion);

        return new AssessRiskResult(assessment);
    }
}
