import React, { useState } from "react";
import ReactDOM from "react-dom";
import Cookies from 'js-cookie';
import LegislatorLookup from "./legislator-lookup";

function OptionInput(props) {
  // props.name, props.value, props.setConfigValue

  return (
    <div>
      <label htmlFor={props.name}>{props.name}</label>
      <input
        id={props.name}
        name={props.name}
        type={props.type}
        value={props.value}
        onChange={(e) => props.setConfigValue(props.name, e.target.value)}
      />
    </div>
  );
}

function getInitialState(options) {
  let state = {
    name: "My Widget",
  };

  for (let opt of options) {
    state[opt.name] = opt.default;
  }
  return state;
}

function Configurator(props) {
  // TODO: get this from props.widgetType
  const options = [
    { name: "bgColor", type: "color", default: "#ffffff" },
    { name: "fgColor", type: "color", default: "#222222" },
  ];

  const [config, setConfig] = useState(getInitialState(options));
  const PreviewElement = LegislatorLookup;

  function setConfigValue(name, value) {
    let newConfig = Object.assign({}, config);
    newConfig[name] = value;
    setConfig(newConfig);
  }

  function saveForm() {
    const csrftoken = Cookies.get("csrftoken");
    fetch("/configure/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
      body: JSON.stringify({...config, widgetType: props.widgetType}),
    }).then(function() {
      // redirect back to index!
      document.location = "/";
    });
  }

  return (
    <div className="config-grid">
      <div>
        <h2>Configuration</h2>

        <OptionInput
          name="name"
          value={config.name}
          setConfigValue={setConfigValue}
        />
        {options.map((o) => (
          <OptionInput
            key={o.name}
            name={o.name}
            type={o.type}
            value={config[o.name]}
            setConfigValue={setConfigValue}
          />
        ))}
        <input type="submit" value="Save Configuration" onClick={saveForm} />
      </div>
      <div>
        <PreviewElement {...config} />
      </div>
    </div>
  );
}

ReactDOM.render(
  React.createElement(Configurator, {widgetType: "SL"}),
  document.getElementById("configurator")
);
