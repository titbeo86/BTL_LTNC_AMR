"""
AMR — Entry point
Chạy: python main.py
"""
from core.application import Application

class AMRSimulation(Application):

    def initialize(self):
        print("=" * 50)
        print("  AMR — Khoi dong thanh cong")
        print("=" * 50)
        print("  Chuot trai  : Dat / xoa vat can")
        print("  Chuot phai  : Dat dich (Goal)")
        print("  SPACE       : Chay Dijkstra tim duong")
        print("  ENTER       : Bat dau mo phong di chuyen")
        print("  R           : Reset robot ve (1,1)")
        print("  N           : Tao ban do ngau nhien moi")
        print("  ESC         : Quay lai man hinh cau hinh")
        print("=" * 50)

    def update(self):
        pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AMR GUI")
    parser.add_argument("--broker", default="192.168.2.9", help="IP của MQTT Broker (mặc định: 192.168.2.9)")
    args = parser.parse_args()

    AMRSimulation(default_broker_ip=args.broker).run()
