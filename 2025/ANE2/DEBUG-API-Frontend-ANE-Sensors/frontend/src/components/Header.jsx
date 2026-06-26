export default function Header({ mac, setMac }) {
    return (
        <div className="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
            <h2 className="mb-0 text-dark" style={{ letterSpacing: '1px', fontWeight: 'bold' }}>
                SDR <span className="text-primary">NEXUS</span> CONTROL
            </h2>
            <div className="input-group" style={{ width: '350px' }}>
                <span className="input-group-text border-primary bg-primary text-white">MAC SENSOR</span>
                <input 
                    type="text" 
                    className="form-control text-center border-primary fw-bold" 
                    value={mac} 
                    onChange={(e) => setMac(e.target.value)} 
                />
            </div>
        </div>
    );
}