// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

using System.Text.Json.Serialization;

namespace Codemotion24.ApiService.Model;

public struct AIChatFile
{
    [JsonPropertyName("contentType")]
    public string ContentType { get; set; }

    [JsonPropertyName("data")]
    public BinaryData Data { get; set; }
}
