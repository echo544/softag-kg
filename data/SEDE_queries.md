## sensitivity (100, 250, 500, 1000)

SELECT COUNT(*) AS EdgeCount
FROM (
    SELECT 
        val.tag AS CoTag,
        COUNT(*) AS CoCount
    FROM Posts p
    CROSS APPLY (
        SELECT value AS tag
        FROM STRING_SPLIT(
            REPLACE(REPLACE(p.Tags, '<', ''), '>', ' '),
            ' '
        )
        WHERE value != ''
    ) val
    WHERE p.PostTypeId = 1
      AND p.Tags LIKE '%<python>%'
    GROUP BY val.tag
    HAVING COUNT(*) >= 500   -- change accordingly
) sub

### results
for 100: 3231
for 250: 1746
for 500: 1066
for 1000: 604

## top250_tags.csv

SELECT TOP 250
    TagName,
    Count AS QuestionCount
FROM Tags
ORDER BY Count DESC

## top250_descriptions.csv

SELECT t.TagName, p.Body
FROM Tags t
JOIN Posts p ON p.Id = t.ExcerptPostId
WHERE t.Count >= (
    SELECT MIN(x.Count)
    FROM (SELECT TOP 250 Count FROM Tags ORDER BY Count DESC) x
)
ORDER BY t.Count DESC

## top250_synonyms.csv

WITH Top250 AS (
    SELECT TOP 250 TagName
    FROM Tags
    ORDER BY Count DESC
)
SELECT
    SourceTagName,
    TargetTagName
FROM TagSynonyms
WHERE SourceTagName IN (SELECT TagName FROM Top250)
   OR TargetTagName  IN (SELECT TagName FROM Top250)

## top250_cooccurrence.csv

### single anchor version for javascript, python, java ONLY

DECLARE @AnchorTag NVARCHAR(50) = 'javascript';     -- ← only change this per query
DECLARE @AnchorCount INT;
SELECT @AnchorCount = [Count] FROM Tags WHERE TagName = @AnchorTag;

WITH Top250 AS (
    SELECT TOP 250 TagName
    FROM Tags
    ORDER BY [Count] DESC
),
LowerTags AS (
    SELECT TagName
    FROM Tags
    WHERE [Count] < @AnchorCount
      AND TagName IN (SELECT TagName FROM Top250)
)
SELECT
    @AnchorTag  AS Tag1,
    v.tag       AS Tag2,
    COUNT(*)    AS CoCount
FROM Posts p
CROSS APPLY (
    SELECT value AS tag
    FROM STRING_SPLIT(
        REPLACE(
            REPLACE(p.Tags, '<', ''),
        '>', ' '),
    ' ')
    WHERE value <> ''
      AND value <> @AnchorTag
      AND value IN (SELECT TagName FROM LowerTags)
) v
WHERE p.PostTypeId = 1
  AND p.Tags LIKE '%<' + @AnchorTag + '>%'
GROUP BY v.tag
HAVING COUNT(*) >= 500
ORDER BY CoCount DESC

### multi anchor version for the remainder of the 250 tags (35 manual queries)

WITH Top250 AS (
    SELECT TOP 250 TagName, [Count]
    FROM Tags
    ORDER BY [Count] DESC
),
AnchorSet AS (
    SELECT TagName AS anchor, [Count] AS acount
    FROM Tags
    WHERE TagName IN ('java', 'c#')  -- change this per query
),
LowerTags AS (
    SELECT a.anchor, t.TagName AS tag
    FROM AnchorSet a
    CROSS JOIN Top250 t
    WHERE t.[Count] < a.acount
      AND t.TagName != a.anchor
)
SELECT
    a.anchor AS Tag1,
    v.tag    AS Tag2,
    COUNT(*) AS CoCount
FROM Posts p
JOIN AnchorSet a ON p.Tags LIKE '%<' + a.anchor + '>%'
CROSS APPLY (
    SELECT s.value AS tag
    FROM STRING_SPLIT(
        REPLACE(
            REPLACE(p.Tags, '<', ''),
        '>', ' '),
    ' ') s
    JOIN LowerTags lt ON lt.tag = s.value AND lt.anchor = a.anchor
    WHERE s.value <> ''
      AND s.value <> a.anchor
) v
WHERE p.PostTypeId = 1
GROUP BY a.anchor, v.tag
HAVING COUNT(*) >= 500
ORDER BY CoCount DESC

#### tag groups (35 queries)
'php', 'ruby'
'android', 'html'
'jquery', 'c++'
'css', 'ios'
'sql', 'mysql'
'r', 'reactjs', 'node.js'
'arrays', 'c'
'asp.net', 'json', 'python-3.x'
'.net', 'ruby-on-rails', 'sql-server', 'swift', 'django'
'angular', 'objective-c', 'excel', 'pandas', 'angularjs', 'regex', 'typescript'
'linux', 'ajax', 'iphone'
'vba', 'xml', 'laravel', 'spring'
'asp.net-mvc', 'database', 'wordpress', 'string'
'flutter', 'postgresql', 'mongodb', 'wpf', 'windows', 'xcode', 'amazon-web-services', 'bash'
'git', 'oracle-database', 'spring-boot', 'dataframe', 'azure', 'firebase', 'list', 'multithreading', 'docker', 'vb.net'
'react-native', 'eclipse', 'algorithm', 'powershell', 'macos', 'visual-studio'
'numpy', 'image', 'forms', 'scala', 'function', 'vue.js', 'performance', 'twitter-bootstrap'
'selenium', 'winforms', 'kotlin', 'loops', 'dart', 'express', 'sqlite', 'hibernate', 'matlab'
'python-2.7', 'shell', 'rest', 'apache', 'entity-framework', 'android-studio', 'csv'
'maven', 'linq', 'qt', 'dictionary', 'unit-testing', 'asp.net-core', 'facebook', 'apache-spark'
'tensorflow', 'file', 'swing', 'class', 'unity-game-engine', 'sorting', 'date'
'authentication', 'go', 'symfony', 't-sql', 'opencv', 'matplotlib', '.htaccess'
'google-chrome', 'for-loop', 'datetime', 'codeigniter', 'perl', 'http', 'validation', 'sockets', 'google-maps', 'object', 'uitableview', 'xaml'
'oop', 'visual-studio-code', 'if-statement', 'cordova', 'ubuntu', 'web-services', 'email', 'android-layout', 'github', 'spring-mvc'
'elasticsearch', 'kubernetes', 'selenium-webdriver', 'ms-access', 'ggplot2', 'user-interface', 'parsing', 'pointers', 'google-sheets', 'c++11'
'security', 'machine-learning', 'google-apps-script', 'ruby-on-rails-3', 'templates', 'flask', 'nginx', 'variables', 'exception'
'sql-server-2008', 'gradle', 'debugging', 'tkinter', 'delphi', 'listview', 'jpa', 'asynchronous', 'haskell', 'web-scraping', 'jsp', 'pdf'
'ssl', 'amazon-s3', 'google-cloud-platform', 'xamarin', 'testing', 'jenkins', 'wcf', 'batch-file', 'generics', 'npm', 'ionic-framework', 'network-programming'
'unix', 'recursion', 'google-app-engine', 'mongoose', 'visual-studio-2010', '.net-core', 'android-fragments', 'assembly', 'animation'
'math', 'svg', 'rust', 'session', 'intellij-idea', 'hadoop', 'join', 'winapi', 'curl', 'django-models', 'laravel-5', 'next.js', 'url', 'heroku', 'http-redirect'
'tomcat', 'inheritance', 'google-cloud-firestore', 'webpack', 'gcc', 'swiftui', 'image-processing', 'keras'
'asp.net-mvc-4', 'logging', 'dom', 'matrix'
'pyspark', 'actionscript-3', 'button', 'post', 'optimization', 'firebase-realtime-database', 'cocoa', 'jquery-ui', 'xpath', 'iis', 'web'
'd3.js', 'javafx', 'firefox', 'xslt', 'internet-explorer', 'caching', 'select', 'asp.net-mvc-3', 'opengl', 'events', 'asp.net-web-api', 'plot'
'dplyr', 'encryption', 'magento', 'stored-procedures', 'search', 'amazon-ec2', 'ruby-on-rails-4', 'memory', 'multidimensional-array', 'canvas', 'audio'

### bash script to join results

```
cp cooc_1.csv top250_cooccurrence.csv
tail -n +2 cooc_2.csv >> top250_cooccurrence.csv
tail -n +2 cooc_3.csv >> top250_cooccurrence.csv
tail -n +2 cooc_4.csv >> top250_cooccurrence.csv
```
etc.