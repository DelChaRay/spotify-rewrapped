"""data_manager module. Contains the needed code to store the input data and query it."""
from typing import Dict
import numpy as np
import pandas as pd

class DataManager:
    """It's main responsability is to store the input data and allow querying it."""
    def __init__(self, files: list):
        """Reads and filters the input data.

        Args:
            files (list): List of paths where the input data is stored.
        """

        # Read input files
        self.df = pd.DataFrame()
        for file in files:
            print(f"Matched input file {file}")
            data_frame = pd.read_json(file)
            self.df = pd.concat([self.df, data_frame], axis=0)

        # Filter and process data
        self.df.endTime = pd.to_datetime(self.df.endTime)
        self.df = self.df[self.df.endTime.dt.year == 2021]
        self.skipped = self.df[self.df.msPlayed <= 10000]
        self.df = self.df[self.df.msPlayed > 10000]

        # Add new columns
        self.df['date'] = self.df.endTime.dt.date
        self.df['month'] = self.df.endTime.dt.month
        self.df['week'] = self.df.endTime.dt.isocalendar().week
        self.df['day_of_week'] = self.df.endTime.dt.dayofweek
        self.df['hour'] = self.df.endTime.dt.hour
        self.df['part_of_the_day'] = pd.cut(self.df.hour,
                                            bins=[-1, 5, 12, 17, 21, 23],
                                            labels=['Night', 'Morning', 'Afternoon',
                                                    'Evening', 'Night'],
                                            ordered=False)
        self.df['hours_played'] = self.df.msPlayed / (60 * 60 * 1000)

    def get_top_n_artists(self, n: int) -> pd.DataFrame:
        """Calculates the N top streamed artists.

        Args:
            n (int): Number of artists

        Returns:
            pd.DataFrame: DataFrame. Columns are artistName and streamed_hours
        """
        return self.df.groupby('artistName')\
                    .agg({'hours_played': np.sum})\
                    .sort_values(by=['hours_played'], ascending=True)\
                    .tail(n)

    def get_streamed_hours_by_time_of_day(self) -> pd.DataFrame:
        """Calcualtes streamed hours by time of the day.

        Returns:
            pd.DataFrame: DataFrame. Index is time of the day and value is total hours_played.
        """
        return self.df.groupby('hour').agg({'hours_played': np.sum})

    def get_streamed_hours_by_day_of_week(self) -> Dict:
        """Calculates streamed hours by day of the week.

        Returns:
            Dict: Keys are [morning, afternoon, evening, night]. Each key contains a list of 7 int
            elements. Each element represents a day of the week and its value is the number of
            streamed hours on the specified part of the day on the specified day of the week.
        """

        day_of_week = self.df.groupby(['part_of_the_day', 'day_of_week'])\
                            .agg({'hours_played': np.sum})

        return {'morning': day_of_week.loc['Morning'],
                'afternoon': day_of_week.loc['Afternoon'],
                'evening': day_of_week.loc['Evening'],
                'night': day_of_week.loc['Night']}

    def get_percent_hours_played_in_top_artists(self, n: int) -> list:
        """Calculates the streamed hours that are contained on the top N streamed artists and
        the streamed hours that are contained on the other artists.

        Args:
            n (int): Number of top artists to set the threshold.

        Returns:
            list: First element is the hours streaming the top N artists, second element is the
            hours streaming other artists.
        """

        artists = list(self.get_top_n_artists(n).index)
        total_hours = self.df.hours_played.sum()
        top_hours = self.df[self.df.artistName.isin(artists)].hours_played.sum()

        return [top_hours, total_hours - top_hours]

    def get_cumsum_by_week(self, n: int):
        """Returns the cumsum of your top N streamed artists. Index is artistName,
        each artist has 52 rows, one for each week of the year."""
        top_artists = self.get_top_n_artists(n)

        df2 = self.df[self.df.artistName.isin(top_artists.index)]
        hours_by_week = pd.DataFrame(columns=['week', 'artist_name', 'hours_played'])
        for i in range(1,53):
            # Join all weekly streams into one by artist
            data = df2[df2.week == i].groupby('artistName')\
                                    .agg({'hours_played': np.sum})
            week_df = pd.DataFrame({'artist_name': data.index,
                                    'week': i,
                                    'hours_played': data.hours_played})
            hours_by_week = hours_by_week.append(week_df)

        # Fill missing weeks
        for artist in list(top_artists.index):
            if hours_by_week[hours_by_week.artist_name == artist].shape[0] < 52:
                for w in range(1, 53):
                    if not hours_by_week[(hours_by_week.artist_name == artist) &
                                         (hours_by_week.week == w)].all(1).any():
                        hours_by_week = hours_by_week.append({'artist_name': artist,
                                                              'week': w,
                                                              'hours_played': 0},
                                                             ignore_index=True)

        hours_by_week = hours_by_week.set_index('artist_name')\
                                    .sort_values(by=['artist_name', 'week'])\
                                    .groupby('artist_name')\
                                    .cumsum()

        return hours_by_week

    def all_i_want_for_christmas_is_you(self):
        """Checks if you streamed at least 1 hour of All I Want for Christmas Is You,
        returns the ammount of hours and True/False on a dictionary."""
        data = self.df[(self.df.trackName.str.startswith('All I Want for Christmas Is You'))]
        hours = 0
        if data.shape[0] > 0:
            hours = data.groupby('trackName')\
                        .agg({'hours_played': np.sum})\
                        .hours_played[0]
        return {'achieved': hours >= 1,
                'hours': hours}

    def deffinitive_halloween_experience(self):
        """Checks if you streamed Thriller on 31/10/2021 or 1/11/2021,
        returns True/False."""
        return self.df[(self.df.trackName == 'Thriller') &
                       (self.df.artistName == 'Michael Jackson') &
                       ((self.df.endTime.dt.month == 10) & (self.df.endTime.dt.day == 31) |
                        (self.df.endTime.dt.month == 11) & (self.df.endTime.dt.day == 1))].shape[0] > 0

    def days_streamed(self):
        """Checks if you streamed at least 1 track each day of 2021,
        returns the ammount of days that you streamed and True/False on a dictionary."""
        days = self.df.groupby('date').size().size
        return {'achieved': days == 365,
                'days': days}

    def variety_is_the_spice_of_life(self):
        """Checks if your hours streaming your top 20 artists are less or equal
        that 0.3 compared to the total streamed hours."""
        top_hours, others_hours = self.get_percent_hours_played_in_top_artists(20)
        return top_hours / (top_hours + others_hours) < 0.3
