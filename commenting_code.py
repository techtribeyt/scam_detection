from googleapiclient.discovery import build
import re
import wordninja
import pickle
import google_auth_oauthlib.flow

def is_scam(comment):
    # load model and vectorizer
    svm = pickle.load(open("scam_model", 'rb'))
    vectorizer = pickle.load(open("vectorizer", 'rb'))
    
    # clean comment (remove punctuation, etc)
    clean_comment = re.sub(r'[^A-Za-z0-9 ]+', '', comment)
    clean_comment = ' '.join(wordninja.split(clean_comment))
    clean_comment = clean_comment.lower()
    
    # transform using vectorizer
    comment_transformed = vectorizer.transform([clean_comment])
    
    # generate prediction
    pred = svm.predict(comment_transformed)
    return pred[0] == 1


def run_analyzer_on_video(video_id):
    # retrieve youtube video results
    video_response=YOUTUBE_BUILD.commentThreads().list(
    part='snippet,replies',
    videoId=video_id,
    textFormat='plainText',
    maxResults=100
    ).execute()

    # iterate video response
    while video_response:
        if SCAMS_DETECTED > DETECTOR_LIMIT:
            return

        # extracting required info
        # from each result object 
        for item in video_response['items']:

            # Extracting comments
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            if is_scam(comment):
                handle_scam_comment(item['snippet']['topLevelComment'], is_parent=True)

            # counting number of reply of comment
            replycount = item['snippet']['totalReplyCount']

            # if a reply is there
            if replycount > 0:

                # iterate through all reply
                if 'replies' in item:
                    for reply in item['replies']['comments']:

                        # Extract reply
                        comment = reply['snippet']['textDisplay']
                        if is_scam(comment):
                            handle_scam_comment(reply)

        # Again repeat
        if 'nextPageToken' in video_response:
            video_response = YOUTUBE_BUILD.commentThreads().list(
                    part = 'snippet,replies',
                    videoId = video_id,
                    textFormat='plainText',
                    pageToken=video_response['nextPageToken'],
                    maxResults=100
                ).execute()
        else:
            break
        
def handle_scam_comment(comment_resource_object, is_parent=False):
    global SCAMS_DETECTED
    SCAMS_DETECTED += 1
    author_name = comment_resource_object['snippet']['authorDisplayName']   
    parent_id = comment_resource_object['id'] if is_parent else comment_resource_object['snippet']['parentId']
    request = YOUTUBE_BUILD.comments().insert(
        part="snippet,id",
        body={
          "snippet": {
            "parentId": parent_id,
            "textOriginal": f"Hey! The comment left above by *{author_name}* is likely a scam based on my machine learning model. I sometimes make errors, so just exercise caution and use your best judgement."
          }
        }
    )
    request.execute()
    
def get_youtube_build():
    # tutorial on how to get the json file: https://support.glitch.com/t/tutorial-youtube-api-making-comments/27828
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "client_secret.json"
    scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]


    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_console()
    youtube = build(
        api_service_name, api_version, credentials=credentials)
    return youtube

# enter video ID
video_id = input("Please enter the video id: ")

# connect to YouTube API and run function
YOUTUBE_BUILD = get_youtube_build()
DETECTOR_LIMIT = 10
SCAMS_DETECTED = 0
run_analyzer_on_video(video_id)