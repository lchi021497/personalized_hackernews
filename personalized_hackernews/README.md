Types of Sites
--------------
1.  official website (e.g. https://www.networkrail.co.uk/stories/why-rails-buckle-in-britain/)
2.  blogs (e.g. https://kerkour.com/rust-async-await-what-is-a-runtime)
3.  github (e.g. https://github.com/logto-io/logto)
4.  archive (e.g. 
5.  pdfs (e.g. https://www.arvindguptatoys.com/arvindgupta/bookofexpts.pdf)
6.  news sites
7.  demo websites (redirect to Google search?)
8.  forum questions

Things to Parse
--------------
1. paragraphs
2. title, subtitles
3. hierarchical links
4. tables (ignore for now)
5. images (ignore for now)

Data Pipeline
--------------
1. HNposts
2. Sites that HNposts direct to
3. Scrapy spider parses site
4. Raw html data passes through data pipeline
5. Processors in data pipeline transforms data
6. Processed data is stored in Mongo DB

Training Pipeline
--------------
1. Load data form Mongo DB
2. Train Doc2Vec unsupervised model to find-tune embedding weights for document classification
3. Use trained Doc2Vec to generate document embeddings to use as features for Kmeans unsupervised classification
4. Identify cluster in Kmeans, allowing users to query against these clusters to find potential documents of interest.


