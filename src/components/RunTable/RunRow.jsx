import moment from "moment";
import React from 'react';
import { MAIN_COLOR } from 'src/utils/const';
import { formatPace, formatRunTime } from 'src/utils/utils';
import styles from './style.module.scss';

const RunRow = ({ runs, run, locateActivity, runIndex, setRunIndex }) => {
  const distance = (run.distance / 1000.0).toFixed(1);
  const pace = run.average_speed;

  const paceParts = pace ? formatPace(pace) : null;

  const heartRate = run.average_heartrate;

  const runTime = formatRunTime(distance,pace);

  // change click color
  const handleClick = (e, runs, run) => {
    const elementIndex = runs.indexOf(run);
    e.target.parentElement.style.color = 'red';

    const elements = document.getElementsByClassName(styles.runRow);
    if (runIndex !== -1 && elementIndex !== runIndex) {
      elements[runIndex].style.color = MAIN_COLOR;
    }
    setRunIndex(elementIndex);
  };

  return (
    <tr
      className={styles.runRow}
      key={run.start_date_local}
      onClick={(e) => {
        handleClick(e, runs, run);
        locateActivity(run);
      }}
    >
      <td>{}</td>
      <td>{distance}km</td>
      {pace && <td>{pace}km/h</td>}
      {/* <td>{heartRate && heartRate.toFixed(0)}</td> */}
      <td>{runTime}</td>
      <td className={styles.runDate}>{moment(run.start_date_local).format("YYYY-MM-DD")}</td>
    </tr>
  );
};

export default RunRow;
