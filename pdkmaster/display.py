from .skill_grammar import SkillFile

__all__ = ["DisplayFile"]

#
# Grammar
#
class DisplayFile(SkillFile):
    def grammar_elem_init(self, sessiondata):
        super().grammar_elem_init(sessiondata)
        self.ast = {"DisplayFile": self.ast["SkillFile"]}
        self.value = {"DisplayFile": self.value["SkillFile"]}
