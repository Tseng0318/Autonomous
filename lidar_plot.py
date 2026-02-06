# lidar_live_plot_30cm.py
# this is the module to plot what the lidar sees, only for references
import math
from time import sleep
from rplidar import RPLidar, RPLidarException

import matplotlib.pyplot as plt


PORT = "/dev/ttyAMA0"      # dont change things in here
BAUD = 115200

CLOSE_MM = 500             # 50 cm, can increase if needed
SPINUP_S = 1.0
MIN_LEN = 5                # iter_scans
PLOT_EVERY_N_SCANS = 1      # update plot every N scan batches


def main():
    lidar = None
    try:
        print(f"[PLOT] Opening LiDAR on {PORT} @ {BAUD} baud")
        lidar = RPLidar(PORT, baudrate=BAUD, timeout=3)

        print("[PLOT] Starting motor...")
        lidar.start_motor()
        sleep(SPINUP_S)

        plt.ion()
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="polar")
        ax.set_title(f"RPLidar Live View (? {CLOSE_MM} mm)")
        ax.set_rmax(CLOSE_MM)
        ax.set_rlabel_position(135)

        scan_i = 0

        for scan in lidar.iter_scans(min_len=MIN_LEN):
            scan_i += 1
            if scan_i % PLOT_EVERY_N_SCANS != 0:
                continue

            thetas = []
            rs = []

            for quality, angle_deg, dist_mm in scan:
                if not dist_mm:
                    continue
                if dist_mm <= 0:
                    continue

                # ONLY keep points within 50 cm
                if dist_mm > CLOSE_MM:
                    continue

                theta = math.radians(angle_deg % 360.0)
                thetas.append(theta)
                rs.append(dist_mm)

            # Redraw plot every scan batch
            ax.cla()
            ax.set_title(f"RPLidar Live View ( {CLOSE_MM} mm)")
            ax.set_rmax(CLOSE_MM)
            ax.set_rlabel_position(135)

            # 0 reference line
            ax.plot([0, 0], [0, CLOSE_MM])

            if rs:
                ax.scatter(thetas, rs, s=10)
                nearest = int(min(rs))
                print(f"[PLOT] Scan {scan_i}: close_pts={len(rs)} nearest_in_30cm={nearest} mm")
            else:
                print(f"[PLOT] Scan {scan_i}: close_pts=0 (no points within 30 cm)")

            plt.pause(0.001)

    except RPLidarException as e:
        print(f"[PLOT] RPLidarException: {e}")
        print("Common causes: wrong PORT, permission issue, or another process using the port.")
    except KeyboardInterrupt:
        print("\n[PLOT] Stopping (Ctrl+C).")
    finally:
        if lidar is not None:
            try:
                lidar.stop()
            except Exception:
                pass
            try:
                lidar.stop_motor()
            except Exception:
                pass
            try:
                lidar.disconnect()
            except Exception:
                pass
        print("[PLOT] LiDAR closed cleanly.")
        try:
            plt.ioff()
            plt.show()
        except Exception:
            pass

if __name__ == "__main__":
    main()
