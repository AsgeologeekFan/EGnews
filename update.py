import feedparser
from datetime import datetime, timedelta, timezone
import json
import requests
import os
import openai

# Example sciencedirect RSS feed URL
rss_url = 'https://rss.sciencedirect.com/publication/science/00137952'

def get_sciencedirect_title(rss_url):
    title_with_urls = []

    # Parse the PubMed RSS feed
    feed = feedparser.parse(rss_url)

    # Calculate the date one week ago
    # one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)

    # Iterate over entries in the PubMed RSS feed and extract abstracts and URLs
    for entry in feed.entries:
        # Get the publication date of the entry
        # published_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')

        # If the publication date is within one week, extract the abstract and URL
        # if published_date >= one_week_ago:
        # Get the abstract and DOI of the entry
        title = entry.title
        # abstract = entry.content[0].value
        doi = entry.link
        title_with_urls.append({"title": title, "doi": doi})

    return title_with_urls

# Get the abstracts from the PubMed RSS feed
sciencedirect_titles = get_sciencedirect_title(rss_url)

access_token = os.getenv('GITHUB_TOKEN')
openaiapikey = os.getenv('OPENAI_API_KEY')

client = openai.OpenAI(api_key=openaiapikey, base_url="https://api.deepseek.com")

def extract_scores(text):
    # Use OpenAI API to get Research Score and Social Impact Score separately
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": "You are an expert and researcher in the area of geological engineering. You are skilled at selecting interesting/novelty research."},
            # {"role": "user", "content": f"Given the text '{text}', evaluate this article with two scores:\n"
            #                             "1. Research Score (0-100): Based on research innovation, methodological rigor, and data reliability.\n"
            #                             "2. Social Impact Score (0-100): Based on public attention, policy relevance, and societal impact.\n"
            #                             "Provide the scores in the following format:\n"
            #                             "Research Score: <score>\n"
            #                             "Social Impact Score: <score>"}
            {"role": "user", "content": f"Given the text '{text}', evaluate whether this article contains the keyword ""shear"" and ""joint""\n"
                                        "Provide the scores in the following format:\n"
                                        "Shear Score: <score>\n"
                                        "Joint Score: <score>"}
        ],
        max_tokens=100,
        temperature=1.3
    )

    generated_text = response.choices[0].message.content.strip()  

    # Extract shear score
    shear_score_start = generated_text.find("Shear Score:")
    shear_score = generated_text[shear_score_start+len("Shear Score:"):].split("\n")[0].strip()

    # Extract joint score
    joint_score_start = generated_text.find("Joint Score:")
    joint_score = generated_text[joint_score_start+len("Joint Score:"):].strip()

    return shear_score, joint_score

# Create an empty list to store each abstract with its scores
new_articles_data = []

for title_data in sciencedirect_titles:
    title = title_data["title"]
    shear_score, joint_score = extract_scores(title_data["title"])
    doi = title_data["doi"]

    new_articles_data.append({
        "title": title,
        "shear_score": shear_score,
        "joint_score": joint_score,
        "doi": doi
    })
    

def create_github_issue(title, body, access_token):
    url = f"https://api.github.com/repos/AsgeologeekFan/EGnews/issues"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "title": title,
        "body": body
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 201:
        print("Issue created successfully!")
    else:
        print("Failed to create issue. Status code:", response.status_code)
        print("Response:", response.text)

# Create issue title and content
issue_title = f"Weekly Article Matching - {datetime.now().strftime('%Y-%m-%d')}"
issue_body = "Below are the article matching results from the past week:\n\n"

for article_data in new_articles_data:
    abstract = article_data["title"]
    shear_score = article_data["shear_score"]
    joint_score = article_data["joint_score"]
    doi = article_data.get("doi", "No DOI available")  # Default to "No DOI available" if DOI field is missing

    issue_body += f"- **Title**: {abstract}\n"
    issue_body += f"  **Shear Score**: {shear_score}\n"
    issue_body += f"  **Joint Score**: {joint_score}\n"
    issue_body += f"  **DOI**: {doi}\n\n"

# Create the issue
create_github_issue(issue_title, issue_body, access_token)