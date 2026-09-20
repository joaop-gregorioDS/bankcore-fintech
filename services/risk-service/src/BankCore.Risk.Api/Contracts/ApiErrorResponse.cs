using System.Text.Json.Serialization;

namespace BankCore.Risk.Api.Contracts;

public sealed class ApiErrorResponse
{
    public ApiErrorResponse(string code, string detail)
    {
        Code = code;
        Detail = detail;
    }

    [JsonPropertyName("code")]
    public string Code { get; }

    [JsonPropertyName("detail")]
    public string Detail { get; }
}
