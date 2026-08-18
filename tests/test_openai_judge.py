"""OpenAI judge adapter — tested with a MOCK client (zero spend). Proves parsing + fail-safe without
any live call; the wiring into EntailmentCheck/CongruenceCheck is exercised too."""
import types
import unittest
from faithful_core.adapters.openai_judge import make_openai_entailment_judge, make_openai_congruence_judge
from faithful_core import EntailmentCheck, CongruenceCheck


def fake_client(content):
    def create(**kw):
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))])
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


class OpenAIJudgeAdapter(unittest.TestCase):
    def test_entailment_parses_supported(self):
        j = make_openai_entailment_judge(client=fake_client('{"verdict":"supported","confidence":0.91,"reason":"entails"}'))
        r = j("Apex returned 12.4%", ["Apex returned 12.4% net."])
        self.assertEqual(r["verdict"], "supported")
        self.assertAlmostEqual(r["confidence"], 0.91)

    def test_unknown_verdict_normalizes_to_abstain(self):
        j = make_openai_entailment_judge(client=fake_client('{"verdict":"maybe","confidence":0.5}'))
        self.assertEqual(j("c", ["e"])["verdict"], "abstain")

    def test_malformed_json_is_failsafe_abstain(self):
        j = make_openai_entailment_judge(client=fake_client("{not json"))
        r = j("c", ["e"])
        self.assertEqual(r["verdict"], "abstain")
        self.assertTrue(r["reason"].startswith("judge_error"))

    def test_congruence_parses_both_axes(self):
        j = make_openai_congruence_judge(client=fake_client('{"on_subject":"violated","kind_ok":"supported","confidence":0.8,"reason":"wrong drug"}'))
        r = j("sitagliptin needs no renal adjustment", ["metformin label..."])
        self.assertEqual(r["on_subject"], "violated")
        self.assertEqual(r["kind_ok"], "supported")

    def test_wires_into_entailment_check(self):
        check = EntailmentCheck(judge=make_openai_entailment_judge(client=fake_client('{"verdict":"violated","confidence":0.9,"reason":"unsupported"}')))
        f = check.run([{"text": "Apex is the best fund ever", "evidence_texts": ["Apex returned 12.4%."]}], {"surface": "compliance"})[0]
        self.assertEqual(f.groundedness, "false")

    def test_wires_into_congruence_check(self):
        check = CongruenceCheck(judge=make_openai_congruence_judge(client=fake_client('{"on_subject":"violated","kind_ok":"supported","confidence":0.8,"reason":"x"}')))
        f = {x.dimension: x for x in check.run([{"text": "c", "evidence_texts": ["e"]}], {"surface": "compliance"})}
        self.assertEqual(f["attribution"].groundedness, "false")
        self.assertEqual(f["overgeneralization"].groundedness, "in_corpus")


if __name__ == "__main__":
    unittest.main()
