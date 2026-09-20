using Microsoft.EntityFrameworkCore;

namespace BankCore.Risk.Infrastructure.Persistence;

public sealed class RiskDbContext(DbContextOptions<RiskDbContext> options) : DbContext(options)
{
    public DbSet<RiskAssessmentEntity> RiskAssessments => Set<RiskAssessmentEntity>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<RiskAssessmentEntity>();
        entity.ToTable("risk_assessments");
        entity.HasKey(item => item.Id);
        entity.Property(item => item.Id).HasColumnName("id");
        entity.Property(item => item.TransactionId).HasColumnName("transaction_id");
        entity.Property(item => item.SourceAccountId).HasColumnName("source_account_id");
        entity.Property(item => item.DestinationAccountId).HasColumnName("destination_account_id");
        entity.Property(item => item.AmountCents).HasColumnName("amount_cents").HasColumnType("bigint");
        entity.Property(item => item.OperationType).HasColumnName("operation_type").HasMaxLength(32).IsRequired();
        entity.Property(item => item.RequestFingerprint).HasColumnName("request_fingerprint").HasMaxLength(64).IsRequired();
        entity.Property(item => item.Decision).HasColumnName("decision").HasMaxLength(16).IsRequired();
        entity.Property(item => item.RiskScore).HasColumnName("risk_score");
        entity.Property(item => item.ReasonsJson).HasColumnName("reasons").HasColumnType("jsonb").IsRequired();
        entity.Property(item => item.RulesVersion).HasColumnName("rules_version").HasMaxLength(64).IsRequired();
        entity.Property(item => item.CreatedAt).HasColumnName("created_at").HasColumnType("timestamp with time zone");
        entity.HasIndex(item => item.TransactionId).IsUnique();
        entity.HasIndex(item => item.RequestFingerprint);
    }
}
