#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.
DEV_MODE_STYLESHEET = """
    html, body {
      background-color: #f1f1f1;
      margin: 0;
      padding: 0;
      font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
      color: #333333;
      font-size: small;
    }

    .container {
      padding: 10px 40px;
      box-sizing: border-box;
      width: 100%;
      max-width: 960px;
      margin: 0 auto;
      background-color: white;
      display: flex;
      min-height: 100vh;
      flex-direction: column;
      justify-content: space-between;
    }

    main .title {
      text-decoration: underline;
    }

    main pre {
      background-color: #efefef;
      border: 1px solid #dddddd;
      border-radius: 2px;
      padding: 8px;
    }

    footer {
      box-sizing: border-box;
      margin-top: 60px;
      border-top: 1px solid #dddddd;
      padding: 20px;
      font-size: small;
      color: #888888;
    }
"""

DEV_MODE_INDEX_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IDEA Web Portal (Dev Mode)</title>
  <link href="StyleSheet.css" rel="stylesheet">
</head>
<body>
<div class="container">
  <main>
    <h3 class="title"> SOCA Web Portal (Dev Mode)</h3>
    <p> When using dev-mode, do not use the Web App served by the backend server.</p>
    <p> Start local front-end server using invoke as shown below: </p>
    <pre>$ invoke web-portal.serve-frontend</pre>

    <br/>
    <p>If you've accidentally landed on this page, click below to open the dev-mode front end app:</p>
    <p><a href="http://localhost:3000/">http://localhost:3000/</a></p>

    <br/>
    <br/>
    <p class="greeting">Happy Coding!</p>
  </main>
  <footer>
    Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
  </footer>
</div>
</body>
</html>
"""
