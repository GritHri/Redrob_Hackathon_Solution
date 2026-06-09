# Redrob_Hackathon_Solution

Diving the Ranking part into sections, we will score on different attributes:

- **Hard filters**: To reduce the total number of candidates we score (Done to respect the 5 min wall-clock time limit mainly). Moreover, we are only required to find and score top 100 candidates if we can filter out candidates with 100% accurasy, we can still maintain high recall overall for top 100. These filters must only evit candidates with 100% gurantee that they aren't fit for the JD.
- **Semantic Search**: To ensure we dont get trapped by misleading keywords, which might happen if we only rely on text search or fuzzy search. We will create embeddings and check the cosine similarity around a Ground Truth type Description to ensure we are semantically close to the ideal candidate which will be curated by hand.
- **Reading Between the Signals**: Reading the Redrob signals and all other minor signals to score candidates. We would find suitable cuts for these 23 signals and other data points present by analyzing the data to ensure we place the right filters. But this is not a hard filters its just gonna effect their final scoring.

We Intend on taking a weighted sum of these scored, giving more weightage to Semantic Search, but taking into account all aspects as covered in the JD. Will handle scenario when 2 candidate has same score as mentioned in documentation.
