using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace BankCore.Risk.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class InitialRiskSchema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "risk_assessments",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    transaction_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_account_id = table.Column<Guid>(type: "uuid", nullable: false),
                    destination_account_id = table.Column<Guid>(type: "uuid", nullable: false),
                    amount_cents = table.Column<long>(type: "bigint", nullable: false),
                    operation_type = table.Column<string>(type: "character varying(32)", maxLength: 32, nullable: false),
                    request_fingerprint = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    decision = table.Column<string>(type: "character varying(16)", maxLength: 16, nullable: false),
                    risk_score = table.Column<int>(type: "integer", nullable: false),
                    reasons = table.Column<string>(type: "jsonb", nullable: false),
                    rules_version = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_risk_assessments", x => x.id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_risk_assessments_request_fingerprint",
                table: "risk_assessments",
                column: "request_fingerprint");

            migrationBuilder.CreateIndex(
                name: "IX_risk_assessments_transaction_id",
                table: "risk_assessments",
                column: "transaction_id",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "risk_assessments");
        }
    }
}
