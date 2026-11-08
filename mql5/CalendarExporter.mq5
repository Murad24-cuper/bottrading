// Attach to one DEMO chart. Exports the next seven days every 15 minutes.
// This utility only writes a CSV; it never opens, modifies, or closes trades.
#property strict
#property script_show_inputs

input int RefreshSeconds = 900;
input int HorizonDays = 7;
input string OutputFile = "calendar_events.csv";

string ImportanceName(const ENUM_CALENDAR_EVENT_IMPORTANCE value)
{
   if(value == CALENDAR_IMPORTANCE_HIGH) return "HIGH";
   if(value == CALENDAR_IMPORTANCE_MODERATE) return "MODERATE";
   return "LOW";
}

string CsvEscape(string value)
{
   StringReplace(value, "\"", "\"\"");
   return "\"" + value + "\"";
}

void ExportCalendar()
{
   datetime server_now = TimeTradeServer();
   datetime utc_now = TimeGMT();
   datetime from = server_now;
   datetime to = server_now + HorizonDays * 86400;
   MqlCalendarValue values[];
   int count = CalendarValueHistory(values, from, to);
   if(count < 0)
   {
      PrintFormat("CalendarValueHistory failed: %d", GetLastError());
      return;
   }
   int handle = FileOpen(OutputFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("Cannot write %s: %d", OutputFile, GetLastError());
      return;
   }
   FileWrite(handle, "time_utc", "currency", "importance", "name", "actual", "forecast", "previous");
   long shift = (long)(server_now - utc_now);
   for(int i = 0; i < count; i++)
   {
      MqlCalendarEvent event;
      MqlCalendarCountry country;
      if(!CalendarEventById(values[i].event_id, event) || !CalendarCountryById(event.country_id, country))
         continue;
      datetime event_utc = (datetime)((long)values[i].time - shift);
      string stamp = TimeToString(event_utc, TIME_DATE|TIME_MINUTES) + ":00+00:00";
      StringReplace(stamp, ".", "-");
      FileWrite(handle, stamp, country.currency, ImportanceName(event.importance), CsvEscape(event.name),
                values[i].HasActualValue() ? DoubleToString(values[i].GetActualValue()/1000000.0, 6) : "",
                values[i].HasForecastValue() ? DoubleToString(values[i].GetForecastValue()/1000000.0, 6) : "",
                values[i].HasPreviousValue() ? DoubleToString(values[i].GetPreviousValue()/1000000.0, 6) : "");
   }
   FileClose(handle);
}

void OnStart()
{
   while(!IsStopped())
   {
      ExportCalendar();
      Sleep(MathMax(60, RefreshSeconds) * 1000);
   }
}
