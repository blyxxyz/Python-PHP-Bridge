<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer;

use blyxxyz\PythonServer\Exceptions\ConnectionLostException;

/**
 * A command bridge that uses standard file input and output to communicate.
 *
 * $in and $out will be treated as file paths. PHP's special mock file paths,
 * like php://stdin and php://fd/{file descriptor}, may be used too.
 */
class StdioCommandServer extends CommandServer
{
    /** @var resource */
    private $in;

    /** @var resource */
    private $out;

    public function __construct(string $in, string $out)
    {
        parent::__construct();
        $this->in = fopen($in, 'r');
        $this->out = fopen($out, 'w');
    }

    public function receive(): array
    {
        $line = fgets($this->in);
        if ($line === false) {
            throw new ConnectionLostException("Can't read from input");
        }
        return json_decode($line, true);
    }

    public function send(array $data)
    {
        $encoded = json_encode($data, JSON_PRESERVE_ZERO_FRACTION);
        if ($encoded === false) {
            $encoded = json_encode($this->encodeThrownException(
                new \RuntimeException(json_last_error_msg())
            ));
        }
        fwrite($this->out, $encoded);
        fwrite($this->out, "\n");
    }

    /**
     * Promote warnings to exceptions. This is vital if stderr is used for
     * communication, because anything else written there will then disrupt
     * the connection.
     *
     * @return mixed
     */
    public static function promoteWarnings()
    {
        return set_error_handler(function (int $errno, string $errstr): bool {
            if (error_reporting() !== 0) {
                throw new \ErrorException($errstr);
            }
            return false;
        });
    }
}
