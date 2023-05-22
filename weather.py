import os
import requests
import pprint
import time
import datetime
import sqlite3 as sq

import exceptions

weather_token = os.getenv("weather_token")
settings_names = (
    "temp",
    "feels",
    "wind_speed",
    "wind_direction",
    "humidity",
    "pressure",
    "sunrise",
    "sunset",
    "localtime",
    "length"
)  # строгое соответсвие с полями users.db
number_of_settings = len(settings_names)


class RealtimeWeather:
    def __init__(self, userid: int):
        self.__userid = userid
        self.__update()

    def display_settings(self):
        params = ("температура🌡",
                  "ощущается как❄",
                  "скорость ветра💨",
                  "направление ветра🧭",
                  "влажность💧",
                  "давление🎈",
                  "восход🌇",
                  "закат🌄",
                  "местное время🕒",
                  "продолжительность светового дня☀",
                  )
        res = '⚙Ваши параметры: '
        for i in range(len(params)):
            if self.__settings[i]:
                res += '\n\n\t' + f'{i + 1}. ' + params[i]
            else:
                res += '\n\n\t' + f'{i + 1}.' + params[i] + '❌'
        return res

    def get_weather(self, city=None, lat=None, lon=None):

        coord = self.__get_coord_by_label(city)
        if coord is not None:
            lat, lon = map(float, coord)

        if lat is not None and lon is not None:
            data = self.__request_by_coord(lat, lon)
            try:
                city = data["name"]
            except Exception as e:
                print(e)
                return "❌ Неизвестный город!"

        elif city is not None and coord is None:
            data = self.__request_by_name(city)
        else:
            raise ValueError("неправильный вызов")

        try:
            city_timezone = data['timezone']
        except Exception as e:
            print(e)
            return "❌ Неизвестный город!"
        else:
            # время
            local_time = datetime.datetime.fromtimestamp(time.time() + time.timezone + city_timezone)
            sign = '+' if city_timezone >= 0 else ''

            # погодные условия
            temp_celsius = data['main']['temp']
            feels_like = data['main']['feels_like']

            wind_speed = data["wind"]["speed"]
            wind_direction = self.__get_wind_direction(data["wind"]["deg"])

            humidity = data["main"]["humidity"]
            pressure = data["main"]["pressure"]

            # солнце
            sunrise_time = datetime.datetime.fromtimestamp(data['sys']['sunrise'] + city_timezone)
            sunset_time = datetime.datetime.fromtimestamp(data['sys']['sunset'] + city_timezone)
            length_of_day = sunset_time - sunrise_time

            params = (
                f'температура: {temp_celsius} C°',
                f'ощущается как: {feels_like} C°',
                f'скорость ветра: {wind_speed} м/с',
                f'направление ветра: {wind_direction}',
                f'влажность: {humidity} %',
                f'давление: {pressure} мм. рт. ст.',
                f'восход: {sunrise_time.strftime("%H:%M")}',
                f'закат: {sunset_time.strftime("%H:%M")}',
                f'местное время: {local_time.strftime("%H:%M")} (UTC{sign}{city_timezone / 3600})',
                f'продолжительность светового дня: {length_of_day}',
            )

            now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            weather_compilation = f'''
            Погода в городе {city.capitalize()} на момент {now} UTC такая:'''

            for i in range(len(params)):
                if self.__settings[i]:
                    weather_compilation += "\n\t" + params[i]

            return weather_compilation

    @staticmethod
    def __get_wind_direction(deg: int):
        delta = 23

        if deg < delta or deg > 360 - delta:
            return "Северный"
        if abs(deg - 90) < delta:
            return "Восточный"
        if abs(deg - 180) < delta:
            return "Южный"
        if abs(deg - 270) < delta:
            return "Западный"
        if 0 < deg < 90:
            return "Северо-восточный"
        if 90 < deg < 180:
            return "Юго-Восточный"
        if 180 < deg < 270:
            return "Юго-Западный"
        if 270 < deg < 360:
            return "Северо-Западный"

    def __save_city(self, lat, lon):
        with sq.connect("users.db") as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET lat=?, lon=? WHERE userid == ?", (lat, lon, self.__userid))

    def del_settings(self, raw_numbers):
        numbers = self.__validate_numbers(raw_numbers)
        to_delete = "=0, ".join(settings_names[int(n) - 1] for n in numbers) + "=0 "
        with sq.connect("users.db") as connection:
            cursor = connection.cursor()
            cursor.execute(f"UPDATE users SET {to_delete} WHERE userid == ? ", (self.__userid,))
        self.__update()

    def add_settings(self, raw_numbers):
        numbers = self.__validate_numbers(raw_numbers)
        to_add = "=1, ".join(settings_names[int(n) - 1] for n in numbers) + "=1 "
        with sq.connect("users.db") as connection:
            cursor = connection.cursor()
            cursor.execute(f"UPDATE users SET {to_add} WHERE userid == ? ", (self.__userid,))
        self.__update()

    @staticmethod
    def __validate_numbers(raw_numbers):
        if not raw_numbers:
            raise exceptions.InvalidParametersList("Список параметров не может быть пустым!")
        raw_settings = raw_numbers.lower().replace("все", " ".join("1 2 3 4 5 6 7 8 9 10"), 1)
        nums = filter(str.isnumeric, raw_settings.split())

        final_nums = filter(lambda n: 0 < n <= number_of_settings, map(int, nums))
        if not final_nums:
            raise exceptions.InvalidParametersList("Неверный список!")
        return final_nums

    @staticmethod
    def coord(text):
        if len(text.split()) == 2 and any(d in text for d in "0123456789"):
            try:
                lat, lon = map(float, text.split())
            except ValueError:
                raise exceptions.InvalidCoord("Неверный формат координат!")
            else:
                return lat, lon
        else:
            return False

    def __update(self):
        with sq.connect("users.db") as connection:
            cursor = connection.cursor()
            all_settings = cursor.execute("SELECT * FROM users WHERE userid == ?", (self.__userid,)).fetchone()
            self.__settings = all_settings[3:]

    @staticmethod
    def __request_by_name(city: str):
        request = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_token}&units=metric")
        data = request.json()
        pprint.pprint(data)
        return data

    @staticmethod
    def __request_by_coord(lat: float, lon):
        lat, lon = float(lat), float(lon)
        if abs(lat) > 90 or abs(lon) > 180:
            raise exceptions.InvalidCoord("❌ Неправильные значения координат")

        request = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_token}&units=metric")
        data = request.json()
        pprint.pprint(data)
        return data

    def link_coord(self, name, lat, lon):
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            return "❌ Неверный формат координат"
        else:
            if abs(lat) > 90 or abs(lon) > 180:
                return "❌ Неверное значение координат"
        self.__add_name_to_db(name, lat, lon)

    def unlink_coord(self, name):
        with sq.connect("users.db") as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM names WHERE label == ? AND userid == ?", (name, self.__userid))

    def __add_name_to_db(self, name, lat, lon):
        with sq.connect("users.db") as connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO names (userid, label, lat, lon) VALUES (?, ?, ?, ?)",
                           (self.__userid, name, lat, lon))

    def __get_coord_by_label(self, label):
        with sq.connect("users.db") as connection:
            cursor = connection.cursor()
            coord = cursor.execute("SELECT lat, lon FROM names WHERE userid==? AND label==?",
                                   (self.__userid, label)).fetchone()
            return coord


def create_db():
    with sq.Connection("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
               userid INTEGER PRIMARY KEY,
               lat TEXT NOT NULL DEFAULT 0,
               lon TEXT NOT NULL DEFAULT 0,
               temp BIT NOT NULL DEFAULT 1,
               feels BIT NOT NULL DEFAULT 1,
               wind_speed BIT NOT NULL DEFAULT 1,
               wind_direction BIT NOT NULL DEFAULT 1,
               humidity BIT NOT NULL DEFAULT 1,
               pressure BIT NOT NULL DEFAULT 1,
               sunrise BIT NOT NULL DEFAULT 1,
               sunset BIT NOT NULL DEFAULT 1,
               localtime BIT NOT NULL DEFAULT 1,
               length BIT NOT NULL DEFAULT 1
                          )""")
        cursor.execute("CREATE TABLE IF NOT EXISTS names (userid INTEGER, label TEXT, lat TEXT, lon TEXT)")


def add_user_to_db(userid):
    with sq.Connection("users.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(f"INSERT INTO users (userid) VALUES (?)", (userid,))
        except sq.IntegrityError:
            pass
