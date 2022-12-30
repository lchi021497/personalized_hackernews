from bs4 import BeautifulSoup
from bs4.element import NavigableString
import requests

def is_paragraph(text, thres):
    return len(text.split(' ')) > thres

def parse_neighbors(start_index, pgraphs, pgraph_len_thres, rolling_window_len, list_as_paragraph=False):
    print('PARSE NEIGHBORs')
    # return number of siblings parsed
    sibling = pgraphs[start_index].next_sibling
    num_count = 1
    end_index = start_index + 1
    
    parsed_neighbors = []
    while sibling is not None and num_count <= rolling_window_len:
        if isinstance(sibling, NavigableString):
            text = sibling.string
        else:
            text = sibling.text
        parsed_neighbors.append(text)

        # reset count if encounter another paragraph. Allow some leeway between
        # paragraphs. (i.e. short text among paragraphs is also parsed as long
        # as it is surrounded by paragraphs)
        if is_paragraph(text, pgraph_len_thres):
            num_count = 0
        elif list_as_paragraph and (sibling.name == 'ol' or sibling.name == 'ul' or sibling.name == 'li'):
            num_count = 0

        if sibling.name == 'p':
            if sibling == pgraphs[end_index]:
                end_index += 1

        num_count += 1
        sibling = sibling.next_sibling

    return parsed_neighbors, end_index

# TODO: improve parsing of paragraphs, lists (bullet points), blockquotes
# TODO: improve parsing for different types of sites (e.g. hn posts, business sites?)
# TODO: keep crawling on site if not enough info?
def parse_paragraphs(pgraphs, pgraph_len_thres, rolling_window_len, list_as_paragraph=False):
    # - identify if a block of text is paragraphs through heuristics (word count)

    # use bs4 to  parse paragraphs
    # heuristic: a <p></p> is a paragraph if either
    # 1. its word count is more than 50
    # 2. it has sibling that is a paragraph (within rolling_window_len distance)

    # heuristic: a <li></li> is to be parsed if
    # 1. it has sibling that is a paragraph

    # heuristic: for certain sites with many lists (e.g. github)
    # 1. treat <li></li> as paragraph
    i = 0
    parsed = []
    while i < len(pgraphs):
        p = pgraphs[i]
        print('parsing paragraph: {} at index {}'.format(p, i))
        if is_paragraph(p.text, pgraph_len_thres):
            parsed.append(p.text)
            local_parsed, end_index = parse_neighbors(i, pgraphs, pgraph_len_thres, rolling_window_len, list_as_paragraph=list_as_paragraph)

            print('local parsed: ', local_parsed)
            parsed += local_parsed
            i = end_index
        else:
            i += 1
    return parsed

if __name__ == '__main__':
    URL = 'https://oa.mg/blog/what-are-the-psychological-benefits-of-believing-in-conspiracy-theories/'
    resp = requests.get(URL)

    soup = BeautifulSoup(resp.content, 'html.parser')
    pgraphs = soup.find_all('p')

    PGRAPH_LEN_THRES = 30
    PGRAPH_ROLLING_WINDOW=5

    parse_paragraphs(pgraphs, PGRAPH_LEN_THRES, PGRAPH_ROLLING_WINDOW)