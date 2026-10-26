import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {I18nProvider, DatePicker, DateInput, DateSegment, Label, Button, Popover, Dialog, Calendar, CalendarGrid, CalendarCell, Heading} from 'react-aria-components';
import {parseDate, parseZonedDateTime} from '@internationalized/date';
import './style.css';

function Field({label, name, value, onChange}) {
  return <DatePicker name={name} value={value} onChange={onChange} granularity="day" isRequired>
    <Label>{label}</Label>
    <div className="field"><DateInput>{segment => <DateSegment segment={segment}/>}</DateInput><Button aria-label={`Choose ${label}`}>Calendar</Button></div>
    <Popover><Dialog><Calendar><header><Button slot="previous">Previous</Button><Heading/><Button slot="next">Next</Button></header><CalendarGrid>{date => <CalendarCell date={date}/>}</CalendarGrid></Calendar></Dialog></Popover>
  </DatePicker>;
}
function App() {
  const [locale,setLocale] = useState('en-US');
  const [date,setDate] = useState(parseDate('2026-11-05'));
  const [appointment,setAppointment] = useState(parseZonedDateTime('2026-11-05T09:30[America/Los_Angeles]'));
  const [payload,setPayload] = useState(null);
  return <main><h1>Same date display, different submitted values</h1><p>Synthetic local specimen. No data is sent. Both fields display only the day; that does not make their values equivalent.</p>
    <label>Display locale <select value={locale} onChange={e => {setLocale(e.target.value);setPayload(null);}}><option value="en-US">English (US)</option><option value="en-GB">English (UK)</option></select></label>
    <I18nProvider locale={locale}><form onSubmit={e => {e.preventDefault();setPayload(Object.fromEntries(new FormData(e.currentTarget)));}}>
      <Field label="Booking day" name="booking_day" value={date} onChange={v => {setDate(v);setPayload(null);}}/>
      <Field label="Appointment with hidden time" name="appointment" value={appointment} onChange={v => {setAppointment(v);setPayload(null);}}/>
      <button type="submit">Inspect submitted values</button>
    </form></I18nProvider>
    <h2>Captured FormData</h2><pre data-testid="payload">{payload ? JSON.stringify(payload,null,2) : 'Submit to inspect the named fields.'}</pre>
    <p>The appointment retains a hidden time on purpose. A real appointment interface must let the customer inspect and confirm its time and zone.</p>
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
