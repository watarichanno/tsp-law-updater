import os
import pathlib
from unittest import mock

import pytest
import toml
import bs4

from tsplawupdater import tsplawupdater


class TestGetBBTag():
    def test_get_bb_tag_from_html_element(self):
        html = bs4.BeautifulSoup(r'<span class="xyz">ABC</span>', 'html.parser')
        lut = {'test': {'name': 'span',
                        'attrs': {'class': ['xyz']},
                        'bb_tag': '[test]{text}[/test]'}}

        tag = tsplawupdater.get_bb_tag(html.contents[0], lut)

        assert tag == '[test]{text}[/test]'

    def test_get_bb_tag_from_html_element_not_on_lut(self):
        html = bs4.BeautifulSoup(r'<span class="efj">ABC</span>', 'html.parser')
        lut = {'test': {'name': 'span',
                        'attrs': {'class': ['xyz']},
                        'bb_tag': '[test]{text}[/test]'}}

        tag = tsplawupdater.get_bb_tag(html.contents[0], lut)

        assert tag == '{text}'


class TestAnchorGenerator():
    def test_gen_anchor(self):
        anchor_lookup_conf = {'section': {'match': r'\((\d+)\) .+',
                                          'anchor_link': r's\g<1>'},
                              'article': {'match': r'(\w+)\. .+',
                                          'anchor_link': r'a\g<1>'},
                              'subsection': {'match': r'([a-z]+)\. .+',
                                             'anchor_link': r'\g<1>'}}
        ins = tsplawupdater.AnchorGenerator(anchor_lookup_conf)

        r1 = ins.gen_anchor('1. ABCD')
        ins.gen_anchor('(1) EFB')
        r2 = ins.gen_anchor('(2) GHJ')
        r3 = ins.gen_anchor('asasaas')
        ins.gen_anchor('2. POL')
        r4 = ins.gen_anchor('(1) AKL')
        r5 = ins.gen_anchor('a. AKL')

        assert r1 == '[anchor=a1][/anchor]'
        assert r2 == '[anchor=a1_s2][/anchor]'
        assert r3 == None
        assert r4 == '[anchor=a2_s1][/anchor]'
        assert r5 == '[anchor=a2_s1_a][/anchor]'


class TestGenBBText():
    def test_gen_bb_text(self):
        bb_lut = {'bold': {'name': 'span',
                           'attrs': {'class': ['bold'],
                                     'style': 'font-weight: bold;'},
                           'bb_tag': '[b]{text}[/b]'},
                  'italic': {'name': 'span',
                             'attrs': {'class': ['italic'],
                                       'style': 'font-style: italic;'},
                             'bb_tag': '[i]{text}[/i]'},
                  'align': {'name': 'div',
                            'attrs': {'class': ['align'],
                                      'style': 'text-align: center;'},
                            'bb_tag': '[align=center]{text}[/align]' }}
        bb_lookup_conf = {'container': 'div[class="container"]',
                          'default_bb_tag': '[p]{text}[/p]',
                          'line_break_html_tag': 'br',
                          'ignore': ['div[class="ignore"]'],
                          'tags': bb_lut}
        anchor_generator = mock.Mock(gen_anchor=mock.Mock(return_value=None))
        html = ('<div class="error">'
                '<span class="italic" style="font-style: italic;">Subtitle</span>'
                '</div>'
                '<div class="container">  \n'
                '<div class="align" style="text-align: center;">  \n'
                '<weird><span class="bold" style="font-weight: bold;">Title</span></weird>  <br />'
                '<span class="italic" style="font-style: italic;">Subtitle</span>  <br />'
                '</div>  '
                '<br />ABCDEF  '
                '<span class="bold" style="font-weight: bold;">  Article</span>'
                '<div class="ignore">abcd</div>'
                '</div>')

        r = tsplawupdater.gen_bb_text(html, bb_lookup_conf, anchor_generator)

        assert r == ('\n[align=center]\n[b][p]Title[/p][/b] \n'
                     '[i][p]Subtitle[/p][/i] \n[/align] '
                     '\n[p]ABCDEF  [/p][b][p]  Article[/p][/b]')


class TestEmbedJinjaTemplate():
    def test_embed_jinja_template_with_existent_std_template_file(self, text_files):
        file_path = text_files({'std.txt': '{% block body %} [law] {% endblock %}'})

        r = tsplawupdater.embed_jinja_template('ABCD', file_path)

        assert r == '{% block body %} ABCD {% endblock %}'

    def test_embed_jinja_template_with_non_existent_std_template_file(self):
        with pytest.raises(FileNotFoundError):
            tsplawupdater.embed_jinja_template('ABCD', pathlib.Path('non-existent.txt'))


class TestUpdateDispatchConfig():
    def test_update_dispatch_config_with_non_existent_file(self, tmp_path):
        laws = {'test1': {'title': 'Test 1', 'url': 'abc'},
                'test2': {'title': 'Test 2', 'url': 'xyz'}}
        file_path = tmp_path / 'dispatch_config.toml'

        tsplawupdater.update_dispatch_config(file_path, 'laws/', laws, 'testopia', 'meta', 'reference')

        expected = {'testopia': {'laws/test1': {'title': 'Test 1', 'category': 'meta', 'subcategory': 'reference'},
                                 'laws/test2': {'title': 'Test 2', 'category': 'meta', 'subcategory': 'reference'}}}
        assert toml.load(file_path) == expected

    def test_update_dispatch_config_with_existing_file_and_edited_config(self, toml_files):
        dispatch_config = {'testopia': {'laws/test1': {'title': 'Test 1', 'ns_id': 12345,
                                                       'category': 'meta', 'subcategory': 'reference'},
                                        'laws/test2': {'title': 'Test 2', 'ns_id': 54321,
                                                       'category': 'meta', 'subcategory': 'reference'}}}
        file_path = toml_files({'dispatch_config.toml': dispatch_config})
        laws = {'test1': {'title': 'Test 1', 'url': 'abc'},
                'test2': {'title': 'Test B', 'url': 'xyz'},
                'test3': {'title': 'Test 3', 'url': 'xyz'}}

        tsplawupdater.update_dispatch_config(file_path, 'laws/', laws, 'testopia', 'meta', 'reference')

        expected = {'testopia': {'laws/test1': {'title': 'Test 1', 'ns_id': 12345, 'category': 'meta', 'subcategory': 'reference'},
                                 'laws/test2': {'title': 'Test B', 'ns_id': 54321, 'category': 'meta', 'subcategory': 'reference'},
                                 'laws/test3': {'title': 'Test 3', 'category': 'meta', 'subcategory': 'reference'}}}
        assert toml.load(file_path) == expected


class TestSaveLawDispatchFile():
    def test_save_law_dispatch_file(self, tmp_path):
        text = 'Test'

        tsplawupdater.save_law_dispatch_file(text, tmp_path, 'test', '.txt')

        assert (tmp_path / 'test.txt').read_text() == 'Test'

