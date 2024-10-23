var builder = DistributedApplication.CreateBuilder(args);

// Add a SQL Server container
var sqlPassword = builder.AddParameter("sql-password");
var sqlServer = builder
    .AddSqlServer("sql", sqlPassword)
    .WithHealthCheck();
var sqlDatabase = sqlServer.AddDatabase("Agency");

// Populate the database with the schema and data
sqlServer
    .WithBindMount("./sql-server", target: "/usr/config")
    .WithBindMount("../../database", target: "/docker-entrypoint-initdb.d")
    .WithEntrypoint("/usr/config/entrypoint.sh");

// Add Data API Builder using dab-config.json 
var dab = builder.AddContainer("dab", "mcr.microsoft.com/azure-databases/data-api-builder", "latest")
    .WithHttpEndpoint(targetPort: 5000, name: "http")
    .WithOtlpExporter()
    .WithBindMount("../../dab/dab-config.json", target: "/App/dab-config.json")
    .WithReference(sqlDatabase)
    .WaitFor(sqlServer);
var dabServiceEndpoint = dab.GetEndpoint("http");

var apiService = builder.AddProject<Projects.Codemotion24_ApiService>("api")
    .WithReference(dabServiceEndpoint);

var frontend = builder.AddNpmApp("frontend", "../frontend", "dev")
    .WithReference(apiService)
    .WithHttpEndpoint(env: "PORT");
    
builder.Build().Run();
