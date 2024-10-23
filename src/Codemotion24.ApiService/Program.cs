using System.Text.Json;
using Codemotion24.ApiService;
using Codemotion24.ApiService.Model;
using Microsoft.SemanticKernel;
using OpenTelemetry;
using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);

// Add service defaults & Aspire components.
builder.AddServiceDefaults();

// Add services to the container.
builder.Services.AddProblemDetails();

var openAIKey = builder.Configuration["OpenAI:ApiKey"];
var otelExporterEndpoint = builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"];

if (string.IsNullOrEmpty(openAIKey)) throw new InvalidOperationException("OpenAIKey is required.");

var loggerFactory = LoggerFactory.Create(builder =>
{
    // Add OpenTelemetry as a logging provider
    builder.AddOpenTelemetry(options =>
    {
        options.AddOtlpExporter(exporter => exporter.Endpoint = new Uri(otelExporterEndpoint));
        // Format log messages. This defaults to false.
        options.IncludeFormattedMessage = true;
    });

    builder.AddTraceSource("Microsoft.SemanticKernel");
    builder.SetMinimumLevel(LogLevel.Warning);
});

using var traceProvider = Sdk.CreateTracerProviderBuilder()
    .AddSource("Microsoft.SemanticKernel*")
    .AddOtlpExporter(exporter => exporter.Endpoint = new Uri(otelExporterEndpoint))
    .Build();

using var meterProvider = Sdk.CreateMeterProviderBuilder()
    .AddMeter("Microsoft.SemanticKernel*")
    .AddOtlpExporter(exporter => exporter.Endpoint = new Uri(otelExporterEndpoint))
    .Build();

builder.Services.AddTransient(builder => {
    var kernelBuilder = Kernel.CreateBuilder();

    kernelBuilder.Services.AddSingleton(loggerFactory);
    
    var kernel = kernelBuilder.AddOpenAIChatCompletion("gpt-4o", openAIKey)  
        .Build();

    return kernel;
});

builder.Services.AddTransient<TravelAgentChat>();

var app = builder.Build();

// Configure the HTTP request pipeline.
app.UseExceptionHandler();

app.MapPost("/api/chat/stream", async (TravelAgentChat travelAgentChat, AIChatRequest request, HttpResponse response) =>
{
    var prompt = request.Messages.Last().Content;

    response.Headers.Append("Content-Type", "application/jsonl");
    var chatResponse = travelAgentChat.ExecuteScenarioStreaming(prompt);
    await foreach (var delta in chatResponse)
    {
        await response.WriteAsync($"{JsonSerializer.Serialize(new AIChatCompletionDelta(new AIChatMessageDelta() { Content = delta }))}\r\n");
        await response.Body.FlushAsync();
    }
});

app.MapDefaultEndpoints();

app.Run();