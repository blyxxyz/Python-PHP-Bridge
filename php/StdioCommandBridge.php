<?php
declare(strict_types = 1);

namespace PythonBridge;

/**
 * A command bridge that uses standard file input and output to communicate.
 *
 * By default, stdin and stderr are used. This is easy to manage because it
 * only uses basic Unix facilities, but it interferes with other use of those
 * streams. In particular, any warning or error that's printed will disrupt
 * the communication. It may be more robust to use named pipes instead.
 *
 * @package PythonBridge
 */
class StdioCommandBridge extends CommandBridge
{
    /** @var resource  */
    private $in;

    /** @var resource */
    private $out;

    public function __construct(
        string $in = "php://stdin",
        string $out = "php://stderr"
    ) {
        $this->in = fopen($in, 'r');
        $this->out = fopen($out, 'w');
    }

    public function receive(): array
    {
        $line = fgets($this->in);
        if ($line === false) {
            throw new \RuntimeException("Can't read from input");
        }
        return json_decode($line, true);
    }

    public function send(array $data)
    {
        $encoded = json_encode($data, JSON_PRESERVE_ZERO_FRACTION);
        if ($encoded === false) {
            $encoded = json_encode([
                'type' => 'thrownException',
                'value' => [
                    'type' => 'JSONEncodeError',
                    'message' => json_last_error_msg()
                ]
            ]);
        }
        fwrite($this->out, $encoded);
        fwrite($this->out, "\n");
    }
}
