import os
import re
import requests
import json
from slackclient import SlackClient

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_ATTACHMENT_COLOR = "#3E7293"
SLACK_TRACKER_EMOJI = ":tracker:"
TRACKER_API_BASE_URL = "https://www.pivotaltracker.com/services/v5/"
TRACKER_API_HEADERS = {"X-TrackerToken": os.getenv("TRACKER_TOKEN")}

story_pattern = re.compile(r"pivotaltracker.com/projects/\d+/stories/(\d+)|pivotaltracker.com/story/show/(\d+)")
line_pattern = re.compile(r"(.*\S)\s+\S*$")

def extract_story_ids(text):
    seen = set()
    return [x[0] if x[1] == '' else x[1] for x in re.findall(story_pattern, text) if not (x in seen or seen.add(x))]

def truncate_line(line, num_chars):
    return line_pattern.match(line[:num_chars]).group(1)
    
def truncate_description(story_description):
    lines = story_description.splitlines(True)
    num_lines = len(lines)
    if num_lines > 5:
        lines = lines[:5]

    result = ""
    for line in lines:
        if len(result) + len(line) <= 140:
            result = result + line
        else:
            return result + truncate_line(line, 140 - len(result)) + "..."
    return result + ("..." if num_lines > 5 else "")

def get_project_name(project_id):
    return requests.get(
        TRACKER_API_BASE_URL + "projects/" + project_id,
        headers=TRACKER_API_HEADERS,
    ).json()["name"]

def get_story(story_id):
    return requests.get(
        TRACKER_API_BASE_URL + "stories/" + story_id,
        headers=TRACKER_API_HEADERS
    ).json()

def post_message(story, channel):
    title = story["name"]
    description = truncate_description(story["description"])
    url = story["url"]
    project_name = SLACK_TRACKER_EMOJI + " " + get_project_name(str(story["project_id"]))
        
    sc.api_call(
        "chat.postMessage",
        channel=channel,
        text="",
        as_user=True,
        attachments=[{
            "fallback": "Story details for " + url,
            "color": SLACK_ATTACHMENT_COLOR,
            "pretext": project_name,
            "title": title,
            "title_link": url,
            "text": description
        }]
    )

if __name__ == '__main__':
    sc = SlackClient(SLACK_TOKEN)
    if sc.rtm_connect():
        while True:
            new_evts = sc.rtm_read()
            for e in new_evts:
                if e["type"] == "message" and "text" in e and "pivotaltracker.com" in e["text"]:
                    channel = e["channel"]
                    for story_id in extract_story_ids(e["text"]):
                        story = get_story(story_id)
                        if story["kind"] == "story":
                            post_message(story, channel)
    else:
        print("Failed to connect to Slack :(((((")
