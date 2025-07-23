# WhatFontis.com API 2.0 Documentation

## API Font Identification from Images

WhatFontIs is the largest independent font detector in the world, helping designers (famous or not) to identify a font regardless of the foundry it was published or the license (free or commercial). We'd like to open the possibility of using 13 years of experience to incorporate that knowledge and experience into your own projects. 

You can do it by submitting an image and getting a list of the 20 most similar fonts. The API expects as input a JSON file and also returns a JSON formatted response. 

**The API is free for personal use, contact us for commercial use.** If you use it for personal purposes we expect (and require) you to include a link to [Whatfontis.com](https://whatfontis.com) on your website. So... start reading and building.

> **Note:** If you make use of the API, a link to [WhatFontis.com](https://whatfontis.com) is required and you may use our logo for this purpose.

## API Response Format

The API returns JSON-encoded objects. Hash keys and values are case-sensitive and character encoding is in UTF-8. Hash keys may be returned in any random order and new keys may be added at any time. We will do our best to notify our users before removing hash keys from results or adding required parameters.

## Rate Limit

By default, you can make up to **200 requests per day**. Requests are associated with the API key, and not with your IP address.

## Error Handling

If an error occurs, a response with proper HTTP error status code is returned. The body of this response contains a description of the issue in plain text. For example, once you go over the rate limit you will receive an HTTP error 429 ("Too Many Requests") with the message "API rate limit exceeded".

### Error Codes

| HTTP Code | Error | Description |
|-----------|-------|-------------|
| 420 | Api ERROR | The API is down |
| 409 | No API key | Include the API key in the JSON payload |
| 429 | Too Many Requests | You are limited to 200 requests per day |
| 422 | MySQL Server Error | There was an error with MySQL |
| 422 | Save Image Error | The image cannot be saved |
| 4221 | Image Type Error | This image type is not yet supported |
| 4222 | Image Size Error | The image is too large |
| 4223 | Textbox Error | No text box detected |
| 422 | No Characters Found | No characters detected in your image. If characters touch or overlap, please separate them |
| 422 | Server Error | Unknown error |

## API Endpoint

### URL Structure
```
https://www.whatfontis.com/api2/
```

### Method
```
POST
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `API_KEY` | string | Yes | Your API key: **8aa7fd702c2669967434cb7e3aa44409b6b8d20281bcc95f5ad074219a84c9e1** |
| `IMAGEBASE64` | int | No | Accepted values: 0, 1<br>• 0 - Use the urlimage<br>• 1 - Use the urlimagebase64, which contains the Base64-encoded image |
| `NOTTEXTBOXSDETECTION` | int | No | Accepted values: 0, 1<br>• 0 - Attempt to locate a textbox containing text<br>• 1 - Attempt to search for characters throughout the entire image |
| `FREEFONTS` | int | No | Accepted values: 0, 1<br>• 0 - All fonts in results<br>• 1 - Only free fonts in results |
| `urlimage` | string | No | URL path to an image |
| `urlimagebase64` | string | No | The Base64-encoded image |
| `limit` | int | No | Determine the number of results<br>Accepted values: 1-20<br>Default: 2 |

## Example Request

To retrieve fonts using a simple image, send a POST request to the API endpoint with the required parameters.

## Example Response

### Response Example 1

Response for this request:

```json
[  
   {  
      "title": "Abril Fatface",
      "url": "https://www.whatfontis.com/FF_Abril-Fatface.font",
      "image": "https://www.whatfontis.com/img16/A/B/FF_Abril-FatfaceA.png"
   },
   {  
      "title": "Didonesque Bold",
      "url": "https://www.whatfontis.com/NMY_Didonesque-Bold.font",
      "image": "https://www.whatfontis.com/img16/D/I/NMY_Didonesque-BoldA.png"
   }
]
```

### Response Keys

| Key | Description |
|-----|-------------|
| `title` | Font title |
| `url` | Font page on WhatFontIs.com |
| `image` | Font image example from WhatFontIs.com |

## Usage Notes

- The API is free for personal use only
- Commercial usage requires contacting WhatFontis.com
- A link back to WhatFontis.com is required for all implementations
- The API returns up to 20 most similar fonts based on your image
- Character encoding is UTF-8
- All requests must include your API key in the JSON payload