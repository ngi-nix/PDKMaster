from skill_grammar import SkillFile


#
# Grammar
#
class DisplayFile(SkillFile):
    def grammar_elem_init(self, sessiondata):
        super().grammar_elem_init(sessiondata)
        self.ast = {"DisplayFile": self.ast["SkillFile"]}
        self.value = {"DisplayFile": self.value["SkillFile"]}
