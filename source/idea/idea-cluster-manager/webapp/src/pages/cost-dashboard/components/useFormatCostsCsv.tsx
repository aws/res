import * as _ from "lodash";
import { useState, useEffect, useRef } from "react";
import { CostExplorerGetTagsResult, GetCostAndUsageResult } from "../../../client/data-model";

export interface ColumnEntry {
  id: string
  displayName: string
}

export interface CSVDownloadParams {
  tagKey: string,
  getTagsResult: CostExplorerGetTagsResult,
  getCostAndUsageResult: GetCostAndUsageResult
}

const useFormatCostsCsv = (csvDownloadParams: CSVDownloadParams) => {
  const [csvData, setCsvData] = useState<any>([]);
  const [csvColumnHeaders, setCsvColumnHeaders] = useState<any>([]);

  const populateHeaders = () => {
    const headers = [{
      id: "timePeriod",
      displayName: csvDownloadParams.tagKey,
    }];
    _.forEach(csvDownloadParams.getTagsResult.Tags, function (value) {
        const tagValueWithDollarSign = value + "($)"
        headers.push({
          id: value,
          displayName: tagValueWithDollarSign
        });
    });
    headers.push({
      id: "totalCosts",
      displayName: "Total costs($)"
    });
    setCsvColumnHeaders(headers);
  }

  const populateCsvData = () => {
    const costTotalsRow: { [key: string]: string } = {timePeriod: csvDownloadParams.tagKey + " total"}
    _.forEach(csvDownloadParams.getTagsResult.Tags, function (value) {
        costTotalsRow[value] = "0";
    });
    const data = [];
    _.forEach(csvDownloadParams.getCostAndUsageResult.ResultsByTime, function (result) {
      const row: { [key: string]: string } = {
        timePeriod: result.TimePeriod.Start,
        totalCosts: "0"
      };
      _.forEach(result.Groups, function (group) {
        const tagValue = group.Keys[0].substring(group.Keys[0].indexOf("$") + 1);
        const cost = group.Metrics.UnblendedCost.Amount;
        row[tagValue] = cost;
        row["totalCosts"] = (Number(row["totalCosts"]) + Number(cost)).toString();
        costTotalsRow[tagValue] = (Number(costTotalsRow[tagValue]) + Number(cost)).toString();
      });
      data.push(row);
    });

    // Aggregate the sums of each project to get total cost over the time period
    let rowSum = 0;
    _.forEach(costTotalsRow, function (value, key) {
      if (value !== undefined && key !== "timePeriod") {
        rowSum = Number(value) + rowSum;
      }
    })
    costTotalsRow["totalCosts"] = rowSum.toString();
    data.unshift(costTotalsRow);
    setCsvData(data);
  }

  useEffect(() => {
    if (csvDownloadParams.getCostAndUsageResult.ResultsByTime !== undefined && csvDownloadParams.getCostAndUsageResult.ResultsByTime.length > 0) {
      populateHeaders();
      populateCsvData();
    }
  }, [csvDownloadParams]);

  return [csvColumnHeaders, csvData];
};

export default useFormatCostsCsv;