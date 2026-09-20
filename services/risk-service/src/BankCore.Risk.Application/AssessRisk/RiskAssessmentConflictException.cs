namespace BankCore.Risk.Application.AssessRisk;

public sealed class RiskAssessmentConflictException : Exception
{
    public RiskAssessmentConflictException(Guid transactionId)
        : base($"A different risk assessment already exists for transaction {transactionId}.")
    {
        TransactionId = transactionId;
    }

    public Guid TransactionId { get; }
}
