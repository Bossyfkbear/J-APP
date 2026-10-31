"""Navigation consolidation: four workspaces, all operations retained."""
from aptk.ui import TOOLS, TOOL_INFO, TOOL_CATEGORY, CATEGORY_TOOLS


def test_exact_four_category_workspaces():
    assert list(CATEGORY_TOOLS)==['轉換與交件','修復','音樂與 AI','音色與檔案']
    assert sum(map(len,CATEGORY_TOOLS.values()))==25
    assert len(set(TOOL_INFO))==25
    assert set(TOOL_CATEGORY)==set(TOOL_INFO)


def test_repair_tools_share_single_workspace():
    assert {'dereverb','residual','declick','declip','deess'}==set(CATEGORY_TOOLS['修復'])


def test_music_ai_tools_share_single_workspace():
    keys=set(CATEGORY_TOOLS['音樂與 AI'])
    assert {'ai_denoise','split','rhythm','pitch','meter','chords','progression','ai_status'}==keys
    assert all(TOOL_CATEGORY[key]=='音樂與 AI' for key in keys)


def test_every_tool_routed_to_one_category():
    all_keys=[key for keys in CATEGORY_TOOLS.values() for key in keys]
    assert len(all_keys)==len(set(all_keys))
    assert all(key in TOOL_INFO for key in all_keys)
