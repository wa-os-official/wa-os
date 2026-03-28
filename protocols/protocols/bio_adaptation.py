"""
Bio-Adaptation Logic for wa-os
土地の環境と個体の調和を計算するプロトコル
"""

class HumanSystem:
    def __init__(self, user_name="Hiroko"):
        self.user_name = user_name
        self.system_stability = 1.0  # 1.0が完全な調和状態
        self.noise_level = 0.0

    def evaluate_input(self, food_data):
        """
        入力された食事データの整合性をチェックする
        """
        # 化学調味料（添加物）チェック
        if food_data.get("artificial_additives"):
            self.noise_level += 0.5
            self.system_stability -= 0.3
            print(f"[Warning] Synaptic noise detected. Stability: {self.system_stability}")
        else:
            self.noise_level *= 0.8 # ノイズの減衰
            print("[Success] Clean input. System resonance is stable.")

        # 土地との調和チェック（身土不二）
        if food_data.get("is_local_season"):
            self.system_stability += 0.2
            print(f"[Sync] Harmonized with local environment: {food_data['location']}")

        return max(0, min(1.0, self.system_stability))

# 実行例（シミュレーション）
if __name__ == "__main__":
    wa_os_user = HumanSystem()
    
    # 昨日のような「調和した食事」の入力例
    dinner_data = {
        "location": "Shiga",
        "artificial_additives": False,
        "is_local_season": True
    }
    
    stability_score = wa_os_user.evaluate_input(dinner_data)
    print(f"Current wa-os Harmony Score: {stability_score}")
