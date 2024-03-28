import os
import re
import zipfile
import anthropic
import streamlit as st
import pandas as pd
import json
from github import Github
from datetime import datetime, timedelta

API_KEY = os.environ.get('ANTHROPIC_API_KEY')
# 깃헙 액세스 토큰
ACCESS_TOKEN = st.secrets["github_token"]

# 깃헙 레퍼지토리 정보
REPO_NAME = 'postAuto'
REPO_OWNER = 'youngouk'

if API_KEY is None:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")


def generate_text(prompt, model="claude-3-opus-20240229", max_tokens=3500, temperature=0.3):
    client = anthropic.Anthropic(api_key=API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return response.content


def extract_tags(body):
    hashtag_pattern = r'(#+[a-zA-Z0-9(_)]{1,})'
    hashtags = [w[1:] for w in re.findall(hashtag_pattern, body)]
    hashtags = list(set(hashtags))
    tag_string = ""
    for w in hashtags:
        if len(w) > 3:
            tag_string += f'{w}, '
    tag_string = re.sub(r'[^a-zA-Z, ]', '', tag_string)
    tag_string = tag_string.strip()[:-1]
    return tag_string


def get_file(filename):
    with open(filename, 'r') as f:
        data = f.read()
    return data


def make_prompt(prompt, topic='<<TOPIC>>', category='<<CATEGORY>>'):
    if topic:
        prompt = prompt.replace('<<TOPIC>>', topic)
    if category:
        prompt = prompt.replace('<<CATEGORY>>', category)
    return prompt


def make_header(topic, category, tags):
    page_head = f'''---
title:  "{topic}"
---'''
    return page_head


def save_blog_post(filename, topic, category, tags, content):
    blog_post = {
        'filename': filename,
        'topic': topic,
        'category': category,
        'tags': tags,
        'content': content,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if 'blog_posts' not in st.session_state:
        st.session_state.blog_posts = []
    st.session_state.blog_posts.append(blog_post)
    with open('blog_posts.json', 'w') as f:
        json.dump(st.session_state.blog_posts, f)
    
    # 깃헙 연결
    g = Github(ACCESS_TOKEN)
    repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")

    # 파일 경로 수정
    file_path = f"blog/posts/{filename}"

    # 블로그 포스트 파일 업로드
    repo.create_file(
        path=filename,        message=f"Add blog post: {topic}",
        content=content,
    )

    # 메타데이터 파일 업로드
    try:
        contents = repo.get_contents("blog_posts.json")
        repo.update_file(
            path='blog_posts.json',
            message="Update blog post metadata",
            content=json.dumps(st.session_state.blog_posts),
            sha=contents.sha
        )
    except:
        repo.create_file(
            path='blog_posts.json',
            message="Create blog post metadata",
            content=json.dumps(st.session_state.blog_posts)
        )


prompt_example = f'''마크다운 문법을 사용하여 블로그 포스트를 작성합니다.
주어진 "<<TOPIC>>" 과 관련된 포스트를 작성하며, 이 포스트의 카테고리는 "<<CATEGORY>>" 입니다.
[분량] 공백 포함 한글 2,000자 내외
[문체] 친근한 설명문 형식. 이모지 활용, 중요 정보 강조, 전문용어 쉬운 표현으로 부가 설명, 의문문 활용 등 블로그 특유의 정보 전달 방식 사용
[신뢰도 제고] 학습된 자료 중 관련 데이터 수치 데이터를 제공하고 출처명시
[가독성 높이기] 300자 내외 문단, 소제목 사용, 시각 자료 활용
[해시태그] 포스트 내용과 관련 해시태그 3~5개를 마지막 라인에 작성합니다.
* 차량 구매에 관심있는 30~50대 한국인을 주요 타겟으로 합니다.
* 포스트 상단에는 글의 요약을 제공합니다.'''

def load_blog_posts():
    try:
        with open('blog_posts.json', 'r') as f:
            st.session_state.blog_posts = json.load(f)
    except FileNotFoundError:
        st.session_state.blog_posts = []

def generate_blog(topic, category, prompt):
    # 사용자 입력(prompt)에 추가적인 예시 텍스트를 포함시킵니다.
    additional_context = """ [예시 포스트 작성-참조 필요]
    ##리스렌트 자동차세 어떻게 납부하나요?
###이 상품을 이용하면 내가 직접 안내도 된다

작성일 2023.12.26.

####인트로
돌아온 12월, 자동차세는 납부하셨나요?

자동차를 구매하면 매년 내야 하는 자동차세. 만약 리스나 장기렌트로 차량을 타고 있다면 어떻게 납부해야 할까요?

오늘은 자동차세란 무엇이고 리스와 장기렌트 이용 시 자동차세를 어떻게 납부하게 되는지에 대해 이야기 나누려 합니다.

####자동차세란 무엇인가요? 👇
🚖 자동차세
자동차세란 자동차를 소유하고 있는 개인이 납부하는 세금입니다. 차량 소유에 대한 재산세의 성격과 도로 이용 등을 통해 발생하는 환경 오염에 대한 부담금의 성격을 동시에 지니고 있습니다.

#####📅 자동차세는 언제 납부 하나요?

자동차세를 납부하는 방법은 두 가지에요. 매년 1월 1년치 자동차세를 한 번에 완납할 수 있으며, 이 경우 약 7%의 감면 혜택을 받을 수 있습니다.

일 년에 두 번으로 나누어 분납도 가능한데요. 이 경우 1기분의 6월, 2기분은 12월로 6개월에 한 번씩 납부합니다. 만약 6월과 12월 차량을 신규 등록한다면 그 달에 한하여 자동차세는 다음 달인 7월 혹은 1월에 고지됩니다.

#####💰 자동차세는 어떻게 산정되나요?

자동차세의 경우 승용차, 승합차, 화물차 등 차종마다 산정 방법이 조금씩 다른데요. 개인용 승용차의 경우 배기량이 기준이 됩니다.

비 영업용 승용차를 기준으로 1,000cc 이하일 때 cc 당 80원, 1,600cc 이하일 때에는 cc 당 140원, 1,600cc를 초과했을 때에는 cc 당 200원이 부과됩니다. cc가 높을수록 자동차세 또한 높은 것이죠.

#####⚡️ 전기차는 자동차세를 어떻게 내나요?

배기량이 없는 전기차의 경우는 예외로 분류되어 비영업용 승용차 기준 대당 10만 원을 납부하고 있는데요. 최근 이 세액에 대한 형평성이 논란이 되며 가격 혹은 차량의 무게를 기준으로 자동차세가 재편될 가능성이 높아지고 있습니다.

🤔 그렇다면 리스나 장기렌트의 경우에는 자동차세를 어떻게 납부할까요?

####리스렌트는 자동차세를 어떻게 낼까?👇
#####📃 리스의 자동차세

리스와 장기렌트 또한 자동차세 납부의 의무에서 예외는 아닌데요.

리스의 자동차세는 차량 구매와 마찬가지로 이용자가 스스로 납부하게 됩니다. 1월 완납 혹은 6월과 12월 두차례 분납이 가능한 것이죠.

#####🧾 장기렌트의 자동차세

장기렌트의 경우 조금 다릅니다. 렌트카 회사에서 자동차세를 먼저 납부하고 이용자는 월 이용료에 나눠 납부하는데요.

그래서 장기렌트의 이용자는 자동차세를 신경 쓸 필요가 없습니다. 고배기량의 자동차라서 자동차세가 부담되거나, 매년 내야하는 자동차세를 챙기기가 불편했던 분들이라면 장기렌트도 좋은 선택이 될 수 있겠네요.

💡 자동차세 납부 이외에도 다양한 리스와 장기렌트의 장점은 리스의 장점과 단점, 장기렌트의 장점과 단점 콘텐츠에서 확인해 보실 수 있습니다.

####🪧 마치며
매년 6월과 12월 납부하는 자동차세. 매년 돌아오는 납부 기간이 조금은 귀찮다면 직접 납부할 필요가 없는 장기렌트는 어떨까요?
    """

    # 최종 프롬프트 생성
    final_prompt = make_prompt(prompt + additional_context, topic=topic, category=category)

    # 수정된 부분: 최종 프롬프트(final_prompt)를 generate_text 함수에 전달
    response = generate_text(prompt=final_prompt)
    body = response

    if isinstance(body, list):
        # 각 ContentBlock 객체에서 문자열 데이터를 추출
        strings = [block.text for block in body]
        # 추출된 문자열 데이터의 리스트를 공백으로 연결
        body = ' '.join(strings)

    tags = extract_tags(body)

    header = make_header(topic=topic, category=category, tags=tags)
    body = '\n'.join(body.strip().split('\n')[1:])
    output = header + body

    yesterday = datetime.now() - timedelta(days=1)
    timestring = yesterday.strftime('%Y-%m-%d')
    filename = f"{timestring}-{'-'.join(topic.lower().split())}.md"
    
    # 블로그 퀄리티 평가 및 피드백 제공
    quality_score, feedback = evaluate_blog_quality(output)

    # 블로그 글 저장
    save_blog_post(filename, topic, category, tags, output)

    return filename, quality_score, feedback

def main():
    st.set_page_config(page_title="Blog Generator", layout="wide")
    load_blog_posts()

    # choice 변수에 '블로그 생성'으로 기본값 할당
    choice = "블로그 생성"

    # 사이드바에 고정형 메뉴 버튼 추가
    st.sidebar.title("메뉴")
    if st.sidebar.button("블로그 생성"):
        choice = "블로그 생성"
    elif st.sidebar.button("생성된 블로그 목록"):
        choice = "생성된 블로그 목록"

    if choice == "블로그 생성":
        # Preset Container
        preset_container = st.container()
        preset_container.subheader('1. 설정')
        tab_single, tab_multiple = preset_container.tabs(['1개 생성', '여러개 생성'])

        col1, col2 = tab_single.columns(2)

        topic = col1.text_input(label='주제 입력', placeholder='주제를 입력해 주세요')
        col1.markdown('(예시)')
        col1.markdown('`차량 구매보다 장기렌트가 유리한 경우 3가지`')

        category = col2.text_input(label='카테고리 입력', placeholder='카테고리를 입력해 주세요')
        col2.markdown('(예시)')
        col2.markdown('`장기렌트`')

        with tab_single:
            # Prompt Container
            prompt_container = st.container()
            prompt_container.subheader('2. 세부지침')
            prompt_container.markdown('`<<TOPIC>>`은 입력한 주제로 `<<CATEGORY>>`는 입력한 카테고리로 **치환되어 세부지침에 입력됩니다.**')
            prompt_container.markdown('[기본 세부지침]')
            prompt_container.markdown(f'''
            ```
            {prompt_example}''')

            prompt = prompt_container.text_area(label='세부지침 입력',
                                                placeholder='지침을 입력하거나, 위 [기본 세부지침]를 복사하여 사용하세요.',
                                                key='prompt1',
                                                height=250)

            # 미리보기 출력
            if prompt:
                prompt_output = make_prompt(prompt=prompt, topic=topic, category=category)
                prompt_container.markdown(f'```{prompt_output}')

            # 블로그 생성
            if topic and category and prompt:
                button = prompt_container.button('생성하기')

                if button:
                    filename, quality_score, feedback = generate_blog(topic=topic, category=category, prompt=prompt)

                    # 깃헙 연결
                    g = Github(ACCESS_TOKEN)
                    repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")

                    # 파일 경로 수정
                    file_path = f"blog/posts/{filename}"

                    try:
                        # 깃헙에서 파일 읽기
                        file_content = repo.get_contents(file_path).decoded_content.decode('utf-8')
                        blog_preview = file_content
                    except:
                        st.error(f"파일을 찾을 수 없습니다: {file_path}")
                        blog_preview = "파일을 찾을 수 없습니다."

                    prompt_container.markdown(blog_preview)

                    # 블로그 퀄리티 점수 및 피드백 출력
                    prompt_container.markdown(f"**블로그 퀄리티 점수**: {quality_score}")
                    prompt_container.markdown(f"**피드백**: {feedback}")

                    # 파일 다운로드 버튼 생성
                    download_btn = prompt_container.download_button(label='파일 다운로드',
                                                                    data=get_file(filename=filename),
                                                                    file_name=filename,
                                                                    mime='text/markdown')

        with tab_multiple:
            file_upload = st.file_uploader("파일 선택(csv)", type=['csv'])
            if file_upload:
                df = pd.read_csv(file_upload)
                df['topic'] = df.apply(lambda x: x['topic'].replace('<<KEYWORD>>', x['keyword']), axis=1)
                st.dataframe(df)

                # Prompt Container
                prompt_container2 = st.container()
                prompt_container2.subheader('2. 세부지침')
                prompt_container2.markdown('[tip 1] **세부지침** 콘텐츠를 생성하는 기준이 됩니다. 별도의 세부지침이 없다면 (예시) 세부지침을 그대로 사용해 주세요')
                prompt_container2.markdown('[tip 2] `<<TOPIC>>`은 입력한 주제로 `<<CATEGORY>>`는 입력한 카테고리로 **치환**됩니다.')
                prompt_container2.markdown('(예시)')
                prompt_container2.markdown(f'''
                ```
                {prompt_example}''')

                prompt2 = prompt_container2.text_area(label='세부지침 입력',
                                                      placeholder='지침을 입력해 주세요',
                                                      key='prompt2',
                                                      height=250)

                total = len(df)
                button2 = prompt_container2.button(f'{total}개 파일 생성하기')

                if button2:
                    generate_progress = st.progress(0)
                    st.write(f"[알림] 총 {total}개의 블로그를 생성합니다!")
                    blog_files = []
                    for i, row in df.iterrows():
                        filename, quality_score, feedback = generate_blog(topic=row['topic'], category=row['category'],
                                                                          prompt=prompt2)
                        blog_files.append(filename)
                        st.write(f"[완료] {row['topic']} (퀄리티 점수: {quality_score}, 피드백: {feedback})")
                        generate_progress.progress((i + 1) / total)

                    yesterday = datetime.now() - timedelta(days=1)
                    timestring = yesterday.strftime('%Y-%m-%d')
                    zip_filename = f'{timestring}-blog-files.zip'
                    with zipfile.ZipFile(zip_filename, 'w') as myzip:
                        for f in blog_files:
                            myzip.write(f)
                        myzip.close()

                    with open(zip_filename, "rb") as fzip:
                        download_btn2 = st.download_button(label="파일 다운로드",
                                                           data=fzip,
                                                           file_name=zip_filename,
                                                           mime="application/zip")

    elif choice == "생성된 블로그 목록":
        st.subheader("생성된 블로그 목록")
        if 'blog_posts' not in st.session_state or len(st.session_state.blog_posts) == 0:
            st.warning("생성된 블로그가 없습니다.")
        else:
            # 블로그 목록 표시
            for post in st.session_state.blog_posts:
                filename = post['filename']
                topic = post['topic']
                category = post['category']
                tags = post['tags']
                created_at = post['created_at']

                # 제목 클릭 시 블로그 내용 표시
                expander = st.expander(topic)
                with expander:
                    st.markdown(f"**카테고리**: {category}")
                    st.markdown(f"**태그**: {tags}")
                    st.markdown(f"**생성일**: {created_at}")

                    # 깃헙 연결
                    g = Github(ACCESS_TOKEN)
                    repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")

                    # 파일 경로 수정
                    file_path = f"blog/posts/{filename}"

                    try:
                        # 깃헙에서 파일 읽기
                        file_content = repo.get_contents(file_path).decoded_content.decode('utf-8')
                        blog_content = file_content
                    except:
                        st.error(f"파일을 찾을 수 없습니다: {file_path}")
                        blog_content = "파일을 찾을 수 없습니다."

                    st.markdown(blog_content)

                    # 파일 다운로드 버튼 생성
                    download_btn = st.download_button(label='파일 다운로드',
                                                      data=get_file(filename=filename),
                                                      file_name=filename,
                                                      mime='text/markdown')



if __name__ == '__main__':
    main()
