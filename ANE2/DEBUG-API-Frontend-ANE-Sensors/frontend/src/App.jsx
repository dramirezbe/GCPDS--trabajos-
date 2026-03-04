import { useState } from 'react';
import Header from './components/Header';
import Controls from './components/Controls';
import ChartDisplay from './components/ChartDisplay';

export default function App() {
    const [mac, setMac] = useState('d0:65:78:9c:dd:d0');
    const [status, setStatus] = useState('STANDBY');
    const [chartData, setChartData] = useState({ labels: [], data: [] });

    return (
        <div className="container-fluid py-4 px-4">
            <Header mac={mac} setMac={setMac} />
            <div className="row">
                <Controls mac={mac} setStatus={setStatus} setChartData={setChartData} />
                <ChartDisplay status={status} chartData={chartData} />
            </div>
        </div>
    );
}