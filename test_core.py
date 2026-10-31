import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from otranslate.core import segmenter
from otranslate.core.dictionary import Dictionary, is_single_word
from otranslate.core.history import History
from otranslate.core.langdetect import detect


class Core(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(detect("The weather is nice and we are going to the beach."), "en")
        self.assertEqual(detect("Le temps est beau et nous allons à la plage."), "fr")
        self.assertIsNone(detect("house"))

    def test_split_keeps_structure(self):
        text = "Dr. Smith went home. It was late!\n\nSecond paragraph here."
        parts = segmenter.split(text)
        sentences = [v for t, v in parts if t]
        self.assertEqual(sentences, ["Dr. Smith went home.", "It was late!", "Second paragraph here."])
        self.assertEqual("".join(v for _, v in parts), text)

    def test_unwrap_pdf(self):
        raw = "This is a long sen-\ntence copied from a\nPDF file. Next one.\n\nNew paragraph."
        out = segmenter.normalize(raw)
        self.assertIn("sentence copied from a PDF file.", out)
        self.assertIn("\n\nNew paragraph.", out)

    def test_single_word(self):
        self.assertTrue(is_single_word("«house»."))
        self.assertFalse(is_single_word("two words"))

    def test_history(self):
        with tempfile.TemporaryDirectory() as d:
            h = History(Path(d) / "h.db")
            h.add("en", "fr", "hello", "bonjour")
            h.add("en", "fr", "hello", "salut")          # dédoublonné
            h.add("fr", "en", "chat", "cat")
            self.assertEqual(len(h.search()), 2)
            self.assertEqual(len(h.search("100%")), 0)
            self.assertEqual(h.search("cha")[0]["target"], "cat")
            h.clear()
            self.assertEqual(h.search(), [])

    def test_dictionary(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "dico.db"
            con = sqlite3.connect(p)
            con.execute("CREATE TABLE entry(id INTEGER PRIMARY KEY, lang, word, word_lc, pos, glosses, synonyms, translations, examples)")
            con.execute("INSERT INTO entry(lang,word,word_lc,pos,glosses,synonyms,translations,examples) VALUES"
                        "('en','House','house','noun','[\"A building\"]','[\"home\"]','[[\"maison\",\"building\"]]','[]')")
            con.commit(); con.close()
            dico = Dictionary(p)
            self.assertEqual(dico.lookup("House.")[0]["translations"], [["maison", "building"]])
            self.assertEqual(dico.guess_lang("house"), "en")
            self.assertEqual(Dictionary(Path(d) / "absent.db").lookup("x"), [])


if __name__ == "__main__":
    unittest.main()
