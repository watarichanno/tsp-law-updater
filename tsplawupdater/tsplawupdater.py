"""A script to keep TSP law dispatch files in sync with TSP forum law archive.
"""

import time
import logging
import logging.config
import re
import unicodedata
import pathlib

import toml
import requests
import bs4

from tsplawupdater import info
from tsplawupdater import utils


LAW_TEXT_PLACEHOLDER = '[law]'

logger = logging.getLogger('tsplawupdater')


def get_bb_tag(html_tag, lut):
    """Get matching BBCode tag of a HTML tag.

    Args:
        html_tag (bs4.Tag): HTML tag.
        lut (list): BBCode tag lookup table.

    Returns:
        str: BBCode tag.
    """

    for tag in lut.values():
        if html_tag.name == tag['name'] and html_tag.attrs == tag['attrs']:
            return tag['bb_tag']

    return '{text}'


class AnchorGenerator():
    """Generate anchor tags based on laws sections and articles.

    Args:
        anchor_lookup_conf (dict): Anchor link lookup config.
    """

    def __init__(self, anchor_lookup_conf):
        sec_conf = anchor_lookup_conf['section']
        self.sec_regex = re.compile(sec_conf['match'])
        self.sec_rep = sec_conf['anchor_link']
        art_conf = anchor_lookup_conf['article']
        self.art_regex = re.compile(art_conf['match'])
        self.art_rep = art_conf['anchor_link']
        ss_conf = anchor_lookup_conf['subsection']
        self.ss_regex = re.compile(ss_conf['match'])
        self.ss_rep = ss_conf['anchor_link']

        self.art = ""
        self.sec = ""

    def gen_anchor(self, text):
        """Generate anchor tags from law's text line

        Args:
            text (str): Text.

        Returns:
            str: Anchor tag.
                 Returns None if no anchor tag can be generated.
        """

        if self.sec_regex.search(text):
            sec = self.sec_regex.sub(self.sec_rep, text)
            self.sec = sec
            link = '{}_{}'.format(self.art, sec)
        elif self.ss_regex.search(text):
            ss = self.ss_regex.sub(self.ss_rep, text)
            link = '{}_{}_{}'.format(self.art, self.sec, ss)
        elif self.art_regex.search(text):
            art = self.art_regex.sub(self.art_rep, text)
            self.art = art
            link = art
        else:
            return None

        return '[anchor={}][/anchor]'.format(link)


def gen_bb_tags(soup, bb_lookup_conf, anchor_generator):
    """Recursively generate BBCode tags from HTML text.

    Args:
        soup (bs4.BeautifulSoup): HTML tags
        bb_lookup_conf (dict): BBCode tag lookup config
        anchor_generator (AnchorGenerator): Anchor generator

    Returns:
        str: BBCode text
    """

    bb_text = ''

    for content in soup.children:
        if content.name == bb_lookup_conf['line_break_html_tag']:
            bb_text += '\n'
        elif isinstance(content, bs4.Tag):
            tag_content_bb_text = gen_bb_tags(content, bb_lookup_conf, anchor_generator)
            bb_tag = get_bb_tag(content, bb_lookup_conf['tags'])
            bb_text += bb_tag.format(text=tag_content_bb_text)
        elif isinstance(content, str):
            if content.isspace():
                bb_text += content
            else:
                text = content.replace('\n', '')
                # Get rid of non-break space.
                clean_text = unicodedata.normalize('NFKD', text.strip())
                anchor = anchor_generator.gen_anchor(clean_text)
                if anchor is not None:
                    bb_text += anchor
                bb_text += bb_lookup_conf['default_bb_tag'].format(text=text)

    return bb_text


def gen_bb_text(html_text, bb_lookup_conf, anchor_generator):
    """Generate BBCode text from HTML text.

    Args:
        html_text (str): HTML text
        bb_lookup_conf (dict): BBCode tag lookup config
        anchor_generator (AnchorGenerator): Anchor generator

    Returns:
        str: BBCode text
    """

    soup = bs4.BeautifulSoup(html_text, 'html.parser')
    soup = soup.select(bb_lookup_conf['container'])[0]

    for selector in bb_lookup_conf['ignore']:
        ignore_tags = soup.select(selector)
        for tag in ignore_tags:
            tag.decompose()

    return gen_bb_tags(soup, bb_lookup_conf, anchor_generator)


def embed_jinja_template(bb_text, std_template_path):
    """Embed Jinja template into law dispatches.

    Args:
        bb_text (str): BBCode text.
        std_template_path (pathlib.Path): Jinja template file path.

    Returns:
        str: BBCode text with Jinja template embedded.
    """

    try:
        return std_template_path.read_text().replace(LAW_TEXT_PLACEHOLDER, bb_text)
    except FileNotFoundError:
        raise FileNotFoundError('Could not find standard law dispatch template file.')


def update_dispatch_config(dispatch_config_path, dispatch_name_prefix, laws, owner_nation, category, subcategory):
    """Update dispatch config file of law dispatches.

    Args:
        dispatch_config_path (pathlib.Path): Dispatch config file path
        dispatch_name_prefix (str): Dispatch name prefix in dispatch config
        laws (dict): Laws
        owner_nation (str): Owner nation of dispatches
        category (str): Dispatch category name
        subcategory (str): Dispatch subcategory name
    """

    dispatch_config = {}

    try:
        dispatch_config = toml.load(dispatch_config_path)[owner_nation]
    except FileNotFoundError:
        logger.info('Create new dispatch config file at %s', dispatch_config_path)

    for name, info in laws.items():
        name = '{}{}'.format(dispatch_name_prefix, name)
        if name not in dispatch_config:
            dispatch_config[name] = {}
        dispatch_config[name]['title'] = info['title']
        dispatch_config[name]['category'] = category
        dispatch_config[name]['subcategory'] = subcategory

    dispatch_config = {owner_nation: dispatch_config}

    with open(dispatch_config_path, 'w') as f:
        toml.dump(dispatch_config, f)


def save_law_dispatch_file(text, template_dir_path, filename, template_ext):
    """Save text into law dispatch file.

    Args:
        text (str): Text
        template_dir_path (pathlib.Path): Path to dispatch template directory
        filename (str): File name
        template_ext (str): File extension
    """

    save_path = (template_dir_path / filename).with_suffix(template_ext)
    with open(save_path, 'w') as f:
        f.write(text)


def main():
    """Starting point."""

    utils.setup_logging_file()
    logging.config.dictConfig(info.LOGGING_CONFIG)

    try:
        config = utils.get_config()
        logger.info('Loaded configuration')
    except FileNotFoundError as err:
        logger.error(err)
        return

    general_conf = config['general']

    update_dispatch_config(pathlib.Path(general_conf['dispatch_config_path']).expanduser(), general_conf['dispatch_name_prefix'],
                            config['laws'], general_conf['owner_nation'], general_conf['category'], general_conf['subcategory'])

    logger.info('Dispatch config updated')

    anchor_generator = AnchorGenerator(config['anchor_lookup'])
    s = requests.Session()

    for name, law_config in config['laws'].items():
        html_text = s.get(law_config['url']).text
        bb_text = gen_bb_text(html_text, config['bb_lookup'], anchor_generator)
        bb_text = embed_jinja_template(bb_text, pathlib.Path(general_conf['std_template_path']).expanduser())
        logger.info('Generated law dispatch "%s"', name)

        save_law_dispatch_file(bb_text, pathlib.Path(general_conf['template_dir_path']).expanduser(),
                               name, general_conf['template_ext'])
        logger.info('Saved law dispatch "%s"', name)
        time.sleep(2)
