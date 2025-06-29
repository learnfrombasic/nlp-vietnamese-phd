from googletrans import Translator

translator = Translator()

async def predict_language(translator: Translator, text: str) -> str:
    result = await translator.detect(text)
    return result


"""

text = "惠 子 謂 莊 子 曰：「魏 王 貽 我 大 瓠 之 種， 我 樹 之 成 而 實 五 石。以 盛 水 漿，其 堅 不 能 自 舉 也。剖 之 以 為 瓢，則 瓠 落 無 所 容。 非 不 呺 然 大 也。吾 為 其 無 用 而 掊 之。」 莊 子 曰：「夫 子 固 拙 於 用 大 矣。宋 人 有 善 為 不 龜 手 之 藥 者，世 世 以 洴 澼 絖 為 事。客 聞 之，請 買 其 方 百 金。聚 族 而 謀 曰：「我 世 世 為 洴 澼 絖，不 過 數 金，今 一 朝 而 鬻 技 百 金，請 與 之。」 客 得 之，以 說 吳 王。越 有 難，吳 王 使 之 將。 冬，與 越 人 水 戰，大 敗 越 人，裂 地 而 封 之。 能 不 龜 手 一 也。或 以 封，或 不 免 於 洴 澼 絖，則 所 用 之 異 也。 今 子 有 五 石 之 瓠，何 不 慮 以 為 大 樽 而 浮 乎 江 湖，而 憂 其 瓠 落 無 所 容 ？ 則 夫 子 猶 有 蓬 之 心 也 夫！」"
result = await predict_language(translator, text)

print(result.lang)  # en
print(result.confidence)    # 1
"""