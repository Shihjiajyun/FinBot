<?php
// 測試語法修復
$index = 0;
$form_number = $index + 1;

// 測試字符串插值
$test_string = "Form 4 #{$form_number}:\n";
echo $test_string;

// 測試數組訪問
$form4 = ['company_name' => 'Test Company', 'report_date' => '2024-01-01'];
$data_summary = "- 公司: {$form4['company_name']}\n";
echo $data_summary;

echo "語法測試完成\n";
