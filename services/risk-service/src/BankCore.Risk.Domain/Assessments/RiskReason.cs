namespace BankCore.Risk.Domain.Assessments;

public sealed record RiskReason
{
    public RiskReason(string code, int points)
    {
        if (string.IsNullOrWhiteSpace(code))
        {
            throw new ArgumentException("Risk reason code is required.", nameof(code));
        }

        if (points < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(points), "Risk reason points cannot be negative.");
        }

        Code = code;
        Points = points;
    }

    public string Code { get; }

    public int Points { get; }
}
