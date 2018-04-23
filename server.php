<?php
declare(strict_types = 1);

namespace PythonBridge;

class PythonBridge
{
    private $in;
    private $out;

    public function __construct(
        $in = "php://stdin",
        $out = "php://stderr"
    )
    {
        $this->in = fopen($in, 'r');
        $this->out = fopen($out, 'w');
    }

    private function receive()
    {
        $line = fgets($this->in);
        if ($line === false) {
            return false;
        }
        return json_decode($line, true);
    }

    private function send($response)
    {
        fwrite($this->out, json_encode($response), JSON_PRESERVE_ZERO_FRACTION);
        fwrite($this->out, "\n");
    }

    private function funcall($data)
    {
        ['func' => $func, 'args' => $args] = $data;
        return $func(...$args);
    }

    private function getConst($data)
    {
        if (!defined($data)) {
            throw new \Exception("Constant $data is not defined");
        }
        return constant($data);
    }

    public function communicate()
    {
        while (($command = $this->receive()) !== false) {
            $cmd = $command["cmd"];
            $data = $command["data"];
            try {
                $ret = ["ret" => [$this, $cmd]($data)];
            } catch (\Throwable $err) {
                // TODO: translate exception types, catch warnings
                $ret = ["err" => $err->getMessage()];
            }
            $this->send($ret);
        }
    }
}

(new PythonBridge)->communicate();
