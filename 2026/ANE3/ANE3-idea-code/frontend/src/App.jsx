import { cfg } from './services/cfg';

function App() {
  // Logic stays outside the return
  console.log("Current API URL:", cfg.API_URL);
  console.log("IS_DEV:", cfg.IS_DEV);

  return (
    <div>
      <h1>API is running on: {cfg.API_URL}</h1>
      <h1>Status: {cfg.IS_DEV ? "Development" : "Production"}</h1>
    </div>
  );
}

export default App;