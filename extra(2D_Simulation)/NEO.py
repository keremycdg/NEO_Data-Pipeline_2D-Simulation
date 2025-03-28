import sqlite3
import requests
import json
import math
import random
from datetime import datetime
import pygame
from pygame.locals import QUIT

def fetch_and_insert_into_sqlite():
    # SQLite database file
    db_path = "neo_db.sqlite"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # NASA CAD API URL (with parameters for date-max, diameter, and fullname)
    url = "https://ssd-api.jpl.nasa.gov/cad.api?date-min=1900-01-01&date-max=2025-01-01&diameter=true&fullname=true"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching data: HTTP {response.status_code}")
        return
    
    # Convert the API response to a Python dict
    json_dataset = response.json()
    fields = json_dataset["fields"]  # List of column names
    rows = json_dataset["data"]      # List of data rows

    # Build the CREATE TABLE statement dynamically: all columns as TEXT.
    # This avoids parse issues if some values don't match numeric types.
    columns_def = ", ".join([f'"{field}" TEXT' for field in fields])
    create_table_query = f"CREATE TABLE IF NOT EXISTS NEO ({columns_def});"
    cursor.execute(create_table_query)
    conn.commit()

    # Optional: Clear existing data from the NEO table
    cursor.execute("DELETE FROM NEO;")
    conn.commit()

    # Build the INSERT statement with placeholders for each column
    placeholders = ", ".join(["?"] * len(fields))
    columns_list = ", ".join([f'"{field}"' for field in fields])
    insert_query = f"INSERT INTO NEO ({columns_list}) VALUES ({placeholders});"

    # Insert all rows from the API into the NEO table
    cursor.executemany(insert_query, rows)
    conn.commit()
    conn.close()
    print("Data inserted into SQLite database successfully.")

if __name__ == "__main__":
    fetch_and_insert_into_sqlite()


# 1 AU in kilometers
AU_IN_KM = 149597870.7

def load_cad_data_from_sqlite(db_path="neo_db.sqlite"):
    """
    Connects to a SQLite database, retrieves all NEO records from the NEO table,
    and returns a list of records with the fields needed for simulation:
      - cd: close-approach date (string, e.g. "2015-Jan-01 00:27")
      - v_rel: relative velocity (km/s)
      - dist: distance (AU)
      - h: absolute magnitude
      - fullname: full name of the object
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Adjust the SQL to match your SQLite table and column names.
        query = "SELECT des, cd, v_rel, dist, h, fullname FROM NEO"
        cursor.execute(query)
        rows = cursor.fetchall()
        data_list = []
        
        for row in rows:
            record = {}
            # row order: des, cd, v_rel, dist, h, fullname
            des_val, cd_val, v_rel_val, dist_val, h_val, fullname_val = row

            # Parse the close-approach date/time from the 'cd' field.
            try:
                # Expecting a format like "2015-Jan-01 00:27"
                record["datetime"] = datetime.strptime(cd_val, "%Y-%b-%d %H:%M")
            except Exception as e:
                print(f"Error parsing date for {des_val}: {e}")
                record["datetime"] = None

            # Parse speed 'v_rel'
            try:
                record["v_rel"] = float(v_rel_val)
            except Exception as e:
                print(f"Error parsing speed for {des_val}: {e}")
                record["v_rel"] = 0.0

            # Parse distance 'dist'
            try:
                record["dist"] = float(dist_val)
            except Exception as e:
                print(f"Error parsing distance for {des_val}: {e}")
                record["dist"] = 0.0

            # Parse absolute magnitude 'h'
            try:
                if h_val is not None:
                    record["h"] = float(h_val)
                else:
                    raise ValueError("h field is None")
            except Exception as e:
                print(f"Error parsing magnitude for {des_val}: {e}")
                record["h"] = None

            # Full name, trim spaces if any
            record["fullname"] = fullname_val.strip() if fullname_val else ""
            record["des"] = des_val

            data_list.append(record)
        
        conn.close()
        
        # Filter out records with invalid dates and sort by datetime.
        data_list = [r for r in data_list if r["datetime"] is not None]
        data_list.sort(key=lambda r: r["datetime"])
        print(f"Loaded {len(data_list)} NEOs from SQLite database.")
        return data_list

    except Exception as e:
        print("Error connecting to SQLite:", e)
        return []


def compute_diameter(h, albedo=0.15):
    """
    Compute the diameter (in meters) from absolute magnitude (h) and albedo.
    Formula: D = 10^(-H/5) * (1329 / sqrt(p)) * 1000 (to convert to meters)
    """
    if h is None:
        return "Unknown"
    try:
        diameter_km = (10 ** (-h / 5)) * (1329 / math.sqrt(albedo))
        diameter_m = diameter_km * 1000
        return f"{diameter_m:.2f} m"
    except Exception as e:
        print(f"Error computing diameter: {e}")
        return "Invalid"


###############################################################################
# Earth Sprite (Rotating)
###############################################################################
class EarthSprite(pygame.sprite.Sprite):
    def __init__(self, x, y, radius_px, image_path="earth.png"):
        super().__init__()
        self.center_x = x
        self.center_y = y
        self.radius_px = radius_px

        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()
            diameter = 2 * radius_px
            self.original_image = pygame.transform.smoothscale(self.original_image, (diameter, diameter))
        except pygame.error:
            print(f"Warning: '{image_path}' not found. Drawing a simple Earth.")
            self.original_image = pygame.Surface((2 * radius_px, 2 * radius_px), pygame.SRCALPHA)
            pygame.draw.circle(self.original_image, (0, 100, 255), (radius_px, radius_px), radius_px)

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.angle = 0

    def update(self):
        self.angle = (self.angle + 0.2) % 360
        self.image = pygame.transform.rotozoom(self.original_image, self.angle, 1.0)
        self.rect = self.image.get_rect(center=(self.center_x, self.center_y))


###############################################################################
# NEO Sprite (Moves from Bottom to Top on Right Side)
###############################################################################
class NEOSprite(pygame.sprite.Sprite):
    def __init__(self, record, earth_center, earth_radius_px, screen_w, screen_h):
        super().__init__()
        self.record = record
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.earth_x, self.earth_y = earth_center
        self.earth_radius_px = earth_radius_px

        self.distance_au = record["dist"]
        self.distance_km = self.distance_au * AU_IN_KM
        self.speed_km_s = record["v_rel"]
        self.h = record.get("h", None)
        self.diameter = compute_diameter(self.h)
        self.full_name = record.get("fullname", "")

        # Determine sprite size based on diameter (fallback default size is 25 pixels)
        try:
            if self.diameter not in ["Unknown", "Invalid"]:
                diameter_value = float(self.diameter.split()[0])
                sprite_size = int(diameter_value / 1.2)
                sprite_size = max(10, min(50, sprite_size))
            else:
                sprite_size = 25
        except Exception:
            sprite_size = 25

        self.image = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (200, 200, 200), (sprite_size // 2, sprite_size // 2), sprite_size // 2)
        self.rect = self.image.get_rect()

        start_x = screen_w - 150  
        start_y = screen_h - 100   
        self.rect.center = (start_x, start_y)

        speed_scale = 0.4
        speed_px_frame = self.speed_km_s * speed_scale
        self.vx = 0
        self.vy = -speed_px_frame

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy

        dx = self.earth_x - self.rect.centerx
        dy = self.earth_y - self.rect.centery
        dist = math.hypot(dx, dy)
        neo_r = self.rect.width / 2

        if dist < (self.earth_radius_px + neo_r):
            self.kill()
            return

        if self.rect.bottom < 0:
            self.kill()

    def draw_name_label(self, surface, font):
        name_text = self.full_name
        name_surf = font.render(name_text, True, (255, 255, 255))
        x = self.rect.centerx - (name_surf.get_width() // 2)
        y = self.rect.centery - self.rect.height - name_surf.get_height()
        surface.blit(name_surf, (x, y))


###############################################################################
# Main Simulation Function
###############################################################################
def run_simulation(data_list):
    pygame.init()
    screen_w, screen_h = 800, 600
    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("NEO Simulation from SQLite Data")

    clock = pygame.time.Clock()

    earth_x, earth_y = 200, 300
    earth_radius_px = 200
    earth_sprite = EarthSprite(earth_x, earth_y, earth_radius_px, "earth.png")
    earth_group = pygame.sprite.GroupSingle(earth_sprite)

    font = pygame.font.SysFont(None, 24)
    n_neos = len(data_list)
    record_index = 0

    running = True
    while running and record_index < n_neos:
        record = data_list[record_index]
        approach_dt = record["datetime"]
        full_name = record.get("fullname", "")

        neo_sprite = NEOSprite(record, (earth_x, earth_y), earth_radius_px, screen_w, screen_h)
        neo_group = pygame.sprite.GroupSingle(neo_sprite)
        print(f"Spawning NEO: {full_name}, Diameter: {neo_sprite.diameter}, Speed: {neo_sprite.speed_km_s} km/s")

        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                    break
            if not running:
                break

            earth_group.update()
            neo_group.update()
            if neo_group.sprite is None:
                break

            screen.fill((0, 0, 0))
            earth_group.draw(screen)
            neo_group.draw(screen)
            neo_group.sprite.draw_name_label(screen, font)

            date_str = approach_dt.strftime("%Y-%b-%d %H:%M")
            top_text = f"{full_name} | {date_str}"
            speed_text = f"Speed: {neo_sprite.speed_km_s:.1f} km/s"
            diameter_text = f"Diameter: {neo_sprite.diameter}"
            combined_text = f"{speed_text} | {diameter_text}"
            top_surf = font.render(top_text, True, (255, 255, 255))
            combined_surf = font.render(combined_text, True, (255, 255, 255))
            screen.blit(top_surf, (10, 10))
            screen.blit(combined_surf, (10, 40))

            dist_text  = f"Closest Flyby Distance: {neo_sprite.distance_km:,.0f} km"
            dist_surf  = font.render(dist_text, True, (255, 255, 255))
            screen.blit(dist_surf, (10, 70))
            count_text = f"{record_index + 1}/{n_neos}"
            count_surf = font.render(count_text, True, (255, 255, 255))
            screen.blit(count_surf, (10, screen_h - 30))

            pygame.display.flip()
            clock.tick(30)
        record_index += 1

    pygame.quit()

def main():
    # Use SQLite instead of MongoDB.
    data_list = load_cad_data_from_sqlite("neo_db.sqlite")
    if not data_list:
        print("No data found in SQLite database or invalid structure.")
        return
    run_simulation(data_list)

if __name__ == "__main__":
    main()