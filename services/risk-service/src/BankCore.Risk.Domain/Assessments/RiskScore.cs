namespace BankCore.Risk.Domain.Assessments;

public readonly record struct RiskScore
{
    public RiskScore(int value)
    {
        if (value is < 0 or > 100)
        {
            throw new ArgumentOutOfRangeException(nameof(value), "Risk score must be between 0 and 100.");
        }

        Value = value;
    }

    public int Value { get; }

    public static RiskScore FromPoints(int points)
    {
        return new RiskScore(Math.Clamp(points, 0, 100));
    }
}
